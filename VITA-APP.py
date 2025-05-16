import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv
import pymongo
from cryptography.fernet import Fernet
from datetime import datetime

load_dotenv()

class VitaAnalyzer:
    def __init__(self):
        self.key1 = os.getenv("gemini-api-key-here")
        genai.configure(api_key=self.key1)
        self.client1 = pymongo.MongoClient(os.getenv("MONGODB_URI"))
        self.db1 = self.client1.vita_db
        self.users1 = self.db1.users
        self.records1 = self.db1.records
        self.key2 = Fernet.generate_key()
        self.cipher = Fernet(self.key2)
    def get_text(self, file):
        t = ""
        try:
            if file.lower().endswith(".pdf"):
                pgs = convert_from_path(file)
                for p in pgs:
                    t += pytesseract.image_to_string(p) + "\n"
            else:
                img = Image.open(file)
                t = pytesseract.image_to_string(img)
            return t
        except Exception as e:
            raise Exception(str(e))
    def analyze(self, txt, typ="quick"):
        if not txt.strip():
            return "No text extracted."
        m = genai.GenerativeModel('gemini-1.5-flash')
        if typ == "quick":
            prompt = f"""
            You are a medical assistant AI. 
            Analyze this medical record and provide a quick summary (max 200 words):
            {txt}
            """
        elif typ == "detailed":
            prompt = f"""
            You are a medical assistant AI. 
            Provide a detailed analysis of this medical record (max 500 words):
            {txt}
            """
        else:
            prompt = f"""
            You are a medical assistant AI. 
            Analyze this medical record focusing on {typ} (max 300 words):
            {txt}
            """
        resp = m.generate_content(prompt)
        return resp.text.strip()
    def save(self, uid, file, ans, typ):
        rec = {
            "user_id": uid,
            "filepath": file,
            "analysis": ans,
            "analysis_type": typ,
            "timestamp": datetime.now(),
            "encrypted": False
        }
        return self.records1.insert_one(rec).inserted_id
    def get_hist(self, uid):
        return list(self.records1.find({"user_id": uid}).sort("timestamp", -1))

class VitaApp:
    def __init__(self):
        self.vita = VitaAnalyzer()
        self.root = ctk.CTk()
        self.root.title("VITA - Medical Record Analyzer")
        self.root.geometry("1200x800")
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.main = ctk.CTkFrame(self.root)
        self.main.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)
        self.header = ctk.CTkFrame(self.main)
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.title_label = ctk.CTkLabel(
            self.header, 
            text="VITA Medical Record Analyzer",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=10)
        self.tabs = ctk.CTkTabview(self.main)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        self.tabs.add("Analysis")
        self.tabs.add("History")
        self.tabs.add("Settings")
        self.make_analysis_tab()
        self.make_history_tab()
        self.make_settings_tab()
        self.user = None
    def make_analysis_tab(self):
        tab = self.tabs.tab("Analysis")
        up = ctk.CTkFrame(tab)
        up.pack(fill="x", padx=20, pady=20)
        self.up_btn = ctk.CTkButton(
            up,
            text="Upload Medical Record",
            command=self.upload,
            font=ctk.CTkFont(size=14)
        )
        self.up_btn.pack(pady=10)
        self.type_opt = ctk.CTkOptionMenu(
            up,
            values=["Quick Summary", "Detailed Analysis", "Condition Focus"],
            font=ctk.CTkFont(size=14)
        )
        self.type_opt.pack(pady=10)
        self.res_box = ctk.CTkTextbox(tab, font=ctk.CTkFont(size=14))
        self.res_box.pack(fill="both", expand=True, padx=20, pady=20)
    def make_history_tab(self):
        tab = self.tabs.tab("History")
        self.hist_list = ctk.CTkScrollableFrame(tab)
        self.hist_list.pack(fill="both", expand=True, padx=20, pady=20)
    def make_settings_tab(self):
        tab = self.tabs.tab("Settings")
        theme = ctk.CTkFrame(tab)
        theme.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(
            theme,
            text="Appearance",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        self.theme_var = ctk.StringVar(value="System")
        theme_menu = ctk.CTkOptionMenu(
            theme,
            values=["System", "Light", "Dark"],
            variable=self.theme_var,
            command=self.change_theme
        )
        theme_menu.pack(pady=10)
    def upload(self):
        file = filedialog.askopenfilename(
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Image files", "*.png *.jpg *.jpeg *.bmp")
            ]
        )
        if not file:
            return
        try:
            txt = self.vita.get_text(file)
            typ = self.type_opt.get().lower().replace(" ", "_")
            ans = self.vita.analyze(txt, typ)
            if self.user:
                self.vita.save(
                    self.user["_id"],
                    file,
                    ans,
                    typ
                )
            self.res_box.delete("1.0", "end")
            self.res_box.insert("1.0", ans)
        except Exception as e:
            messagebox.showerror("Error", str(e))
    def change_theme(self, t):
        ctk.set_appearance_mode(t)
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VitaApp()
    app.run() 
