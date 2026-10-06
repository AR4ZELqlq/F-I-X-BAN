import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

APP = "F!X BAN"

class API:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")
        self.token = None

    def request(self, method, path, payload=None):
        body = None
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")

        req = Request(self.base + path, data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            try:
                data = json.loads(e.read().decode("utf-8"))
            except Exception:
                data = {"ok": False, "error": f"HTTP {e.code}"}
            return data
        except URLError as e:
            return {"ok": False, "error": f"Network error: {e.reason}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

class Login(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP + " • Login")
        self.geometry("560x620")
        self.configure(bg="#080808")
        self.resizable(False, False)

        tk.Label(self, text="F!X BAN", fg="white", bg="#080808",
                 font=("Segoe UI", 32, "bold")).pack(pady=(55, 5))
        tk.Label(self, text="INTERNET MANAGEMENT SYSTEM", fg="#888888", bg="#080808",
                 font=("Segoe UI", 9, "bold")).pack(pady=(0, 40))

        box = tk.Frame(self, bg="#101010")
        box.pack(fill="x", padx=70, pady=10)

        self.url = self.field(box, "SERVER URL", "https://YOUR-SERVER.example.com")
        self.username = self.field(box, "USERNAME", "")
        self.password = self.field(box, "PASSWORD", "", True)

        self.status = tk.Label(self, text="", fg="#ff6666", bg="#080808",
                               font=("Segoe UI", 9))
        self.status.pack(pady=8)

        tk.Button(self, text="SIGN IN", command=self.login, bg="#eeeeee", fg="#080808",
                  relief="flat", font=("Segoe UI", 11, "bold"), padx=20, pady=12,
                  cursor="hand2").pack(fill="x", padx=70, pady=14)

        tk.Label(self, text="No LAN required • Connect from anywhere with internet",
                 fg="#666666", bg="#080808", font=("Segoe UI", 8)).pack()

        self.bind("<Return>", lambda e: self.login())

    def field(self, parent, label, value, secret=False):
        tk.Label(parent, text=label, fg="#888888", bg="#101010",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=22, pady=(18, 4))
        e = tk.Entry(parent, bg="#191919", fg="white", insertbackground="white",
                     relief="flat", font=("Segoe UI", 11),
                     show="•" if secret else "")
        e.pack(fill="x", padx=22, ipady=9, pady=(0, 3))
        e.insert(0, value)
        return e

    def login(self):
        url = self.url.get().strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            self.status.config(text="Server URL must start with http:// or https://")
            return
        api = API(url)
        r = api.request("POST", "/api/login",
                        {"username": self.username.get().strip(),
                         "password": self.password.get()})
        if not r.get("ok"):
            self.status.config(text=r.get("error", "Login failed."))
            return
        api.token = r["token"]
        self.destroy()
        Dashboard(api, r["user"]).mainloop()

class Dashboard(tk.Tk):
    def __init__(self, api, user):
        super().__init__()
        self.api = api
        self.user = user
        self.people = []
        self.users = []
        self.title(APP + " • Control Center")
        self.geometry("1240x760")
        self.minsize(1000, 650)
        self.configure(bg="#080808")
        self.style()
        self.build()
        self.refresh_people()
        if user["role"] == "admin":
            self.refresh_users()

    def style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("Treeview", background="#121212", foreground="#eeeeee",
                    fieldbackground="#121212", rowheight=35, borderwidth=0,
                    font=("Segoe UI", 9))
        s.configure("Treeview.Heading", background="#202020", foreground="#ffffff",
                    font=("Segoe UI", 9, "bold"), padding=8)
        s.map("Treeview", background=[("selected", "#3b3b3b")])
        s.configure("TCombobox", fieldbackground="#181818", background="#181818",
                    foreground="white")

    def build(self):
        header = tk.Frame(self, bg="#0d0d0d", height=78)
        header.pack(fill="x")
        tk.Label(header, text="F!X BAN", fg="white", bg="#0d0d0d",
                 font=("Segoe UI", 25, "bold")).pack(side="left", padx=28, pady=17)
        role = "ADMIN" if self.user["role"] == "admin" else "VIEWER"
        tk.Label(header, text=f"{self.user['username'].upper()}  •  {role}",
                 fg="#999999", bg="#0d0d0d", font=("Segoe UI", 9, "bold")).pack(
                     side="right", padx=28)

        body = tk.Frame(self, bg="#080808")
        body.pack(fill="both", expand=True, padx=22, pady=22)

        side = tk.Frame(body, bg="#101010", width=225)
        side.pack(side="left", fill="y", padx=(0,18))
        side.pack_propagate(False)
        tk.Label(side, text="CONTROL CENTER", fg="#777777", bg="#101010",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(22,12))
        self.nav(side, "PEOPLE", self.show_people)
        if self.user["role"] == "admin":
            self.nav(side, "ADD PERSON", self.add_person)
            self.nav(side, "USER ACCESS", self.user_access)
        self.nav(side, "REFRESH", self.refresh_people)
        tk.Label(side, text="ACCESS", fg="#777777", bg="#101010",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(35,6))
        tk.Label(side, text="● ONLINE", fg="#d8d8d8", bg="#101010",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18)

        self.main = tk.Frame(body, bg="#080808")
        self.main.pack(side="left", fill="both", expand=True)
        self.show_people()

    def nav(self, parent, text, command):
        tk.Button(parent, text=text, command=command, anchor="w",
                  bg="#101010", fg="#eeeeee", activebackground="#272727",
                  activeforeground="white", relief="flat", bd=0,
                  font=("Segoe UI", 10, "bold"), padx=18, pady=12,
                  cursor="hand2").pack(fill="x", padx=8, pady=2)

    def clear(self):
        for w in self.main.winfo_children():
            w.destroy()

    def show_people(self):
        self.clear()
        tk.Label(self.main, text="PEOPLE DIRECTORY", fg="white", bg="#080808",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(self.main, text="Shared online directory",
                 fg="#777777", bg="#080808", font=("Segoe UI", 9)).pack(anchor="w", pady=(3,18))

        card = tk.Frame(self.main, bg="#101010")
        card.pack(fill="both", expand=True)
        cols = ("id","first","last","age","birth","phone")
        self.tree = ttk.Treeview(card, columns=cols, show="headings")
        names = {"id":"ID","first":"FIRST NAME","last":"LAST NAME",
                 "age":"AGE","birth":"DATE OF BIRTH","phone":"PHONE"}
        widths = {"id":55,"first":160,"last":160,"age":70,"birth":150,"phone":180}
        for c in cols:
            self.tree.heading(c, text=names[c])
            self.tree.column(c, width=widths[c], anchor="center")
        self.tree.pack(fill="both", expand=True, padx=14, pady=14)
        self.tree.bind("<Double-1>", self.view_selected)

        if self.user["role"] == "admin":
            buttons = tk.Frame(self.main, bg="#080808")
            buttons.pack(fill="x", pady=10)
            for label, cmd in [("ADD PERSON", self.add_person),
                               ("EDIT SELECTED", self.edit_selected),
                               ("DELETE SELECTED", self.delete_selected)]:
                tk.Button(buttons, text=label, command=cmd, bg="#eeeeee", fg="#080808",
                          relief="flat", font=("Segoe UI",9,"bold"),
                          padx=14, pady=8).pack(side="left", padx=(0,8))
        self.populate_people()

    def populate_people(self):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
        self.tree.delete(*self.tree.get_children())
        for p in self.people:
            self.tree.insert("", "end", values=(p["id"], p["first_name"], p["last_name"],
                                                p["age"], p["birth_date"], p["phone"]))

    def refresh_people(self):
        def work():
            r = self.api.request("GET", "/api/people")
            if r.get("ok"):
                self.after(0, lambda: self.set_people(r["people"]))
            else:
                self.after(0, lambda: messagebox.showerror(APP, r.get("error","Could not load data."), parent=self))
        threading.Thread(target=work, daemon=True).start()

    def set_people(self, people):
        self.people = people
        self.populate_people()

    def view_selected(self, _=None):
        item = self.tree.selection()
        if not item: return
        pid = int(self.tree.item(item[0], "values")[0])
        p = next(x for x in self.people if x["id"] == pid)
        win = tk.Toplevel(self)
        win.title("Person Profile")
        win.geometry("520x480")
        win.configure(bg="#0c0c0c")
        tk.Label(win, text="PERSON PROFILE", fg="white", bg="#0c0c0c",
                 font=("Segoe UI", 18, "bold")).pack(pady=25)
        for label,key in [("FIRST NAME","first_name"),("LAST NAME","last_name"),
                          ("AGE","age"),("DATE OF BIRTH","birth_date"),("PHONE","phone")]:
            row=tk.Frame(win,bg="#151515"); row.pack(fill="x",padx=30,pady=5)
            tk.Label(row,text=label,width=18,anchor="w",fg="#777777",bg="#151515",
                     font=("Segoe UI",8,"bold")).pack(side="left",padx=12,pady=12)
            tk.Label(row,text=str(p[key]),anchor="w",fg="white",bg="#151515",
                     font=("Segoe UI",10,"bold")).pack(side="left",padx=8)

    def person_form(self, existing=None):
        win = tk.Toplevel(self)
        win.title("Add Person" if not existing else "Edit Person")
        win.geometry("520x600")
        win.configure(bg="#0c0c0c")
        tk.Label(win,text="ADD PERSON" if not existing else "EDIT PERSON",
                 fg="white",bg="#0c0c0c",font=("Segoe UI",20,"bold")).pack(pady=(25,20))
        form=tk.Frame(win,bg="#0c0c0c"); form.pack(fill="both",expand=True,padx=40)
        fields=[("FIRST NAME","first_name"),("LAST NAME","last_name"),("AGE","age"),
                ("DATE OF BIRTH","birth_date"),("PHONE","phone")]
        entries={}
        for label,key in fields:
            tk.Label(form,text=label,fg="#888888",bg="#0c0c0c",
                     font=("Segoe UI",8,"bold")).pack(anchor="w",pady=(5,3))
            e=tk.Entry(form,bg="#181818",fg="white",insertbackground="white",
                       relief="flat",font=("Segoe UI",11))
            e.pack(fill="x",ipady=9,pady=(0,8))
            if existing: e.insert(0,str(existing[key]))
            entries[key]=e
        def save():
            data={k:v.get().strip() for k,v in entries.items()}
            if existing:
                r=self.api.request("PUT",f"/api/people/{existing['id']}",data)
            else:
                r=self.api.request("POST","/api/people",data)
            if r.get("ok"):
                win.destroy(); self.refresh_people()
            else: messagebox.showerror(APP,r.get("error","Operation failed."),parent=win)
        tk.Button(form,text="SAVE",command=save,bg="#eeeeee",fg="#080808",
                  relief="flat",font=("Segoe UI",10,"bold"),pady=11).pack(fill="x",pady=20)

    def add_person(self): self.person_form()

    def selected_person_id(self):
        item=self.tree.selection()
        if not item:
            messagebox.showinfo(APP,"Select a person first.",parent=self); return None
        return int(self.tree.item(item[0],"values")[0])

    def edit_selected(self):
        pid=self.selected_person_id()
        if pid is None:return
        p=next(x for x in self.people if x["id"]==pid)
        self.person_form(p)

    def delete_selected(self):
        pid=self.selected_person_id()
        if pid is None:return
        if messagebox.askyesno(APP,"Delete this person?",parent=self):
            r=self.api.request("DELETE",f"/api/people/{pid}")
            if r.get("ok"): self.refresh_people()
            else: messagebox.showerror(APP,r.get("error","Delete failed."),parent=self)

    def user_access(self):
        self.clear()
        tk.Label(self.main,text="USER ACCESS",fg="white",bg="#080808",
                 font=("Segoe UI",20,"bold")).pack(anchor="w")
        tk.Label(self.main,text="Create users and control administrator permissions.",
                 fg="#777777",bg="#080808").pack(anchor="w",pady=(3,18))
        form=tk.Frame(self.main,bg="#101010");form.pack(fill="x")
        self.new_user=self.inline(form,"USERNAME")
        self.new_pass=self.inline(form,"PASSWORD")
        self.new_role=ttk.Combobox(form,values=["user","admin"],state="readonly",width=10)
        self.new_role.set("user");self.new_role.pack(side="left",padx=8,pady=18)
        tk.Button(form,text="ADD USER",command=self.create_user,bg="#eeeeee",fg="#080808",
                  relief="flat",font=("Segoe UI",9,"bold"),padx=15,pady=9).pack(side="left",padx=8)

        card=tk.Frame(self.main,bg="#101010");card.pack(fill="both",expand=True,pady=18)
        self.user_tree=ttk.Treeview(card,columns=("id","username","role","created"),show="headings")
        for c,w in [("id",60),("username",220),("role",130),("created",240)]:
            self.user_tree.heading(c,text=c.upper());self.user_tree.column(c,width=w,anchor="center")
        self.user_tree.pack(fill="both",expand=True,padx=14,pady=14)
        self.populate_users()

        b=tk.Frame(self.main,bg="#080808");b.pack(fill="x",pady=10)
        for label,cmd in [("MAKE ADMIN",lambda:self.role("admin")),
                          ("MAKE VIEWER",lambda:self.role("user")),("DELETE USER",self.delete_user)]:
            tk.Button(b,text=label,command=cmd,bg="#eeeeee",fg="#080808",
                      relief="flat",font=("Segoe UI",9,"bold"),padx=14,pady=8).pack(side="left",padx=(0,8))

    def inline(self,parent,label):
        f=tk.Frame(parent,bg="#101010");f.pack(side="left",padx=8,pady=15)
        tk.Label(f,text=label,fg="#777777",bg="#101010",font=("Segoe UI",8,"bold")).pack(anchor="w")
        e=tk.Entry(f,width=18,bg="#1a1a1a",fg="white",insertbackground="white",relief="flat")
        e.pack(ipady=7,pady=3);return e

    def refresh_users(self):
        def work():
            r=self.api.request("GET","/api/users")
            if r.get("ok"): self.after(0,lambda:self.set_users(r["users"]))
        threading.Thread(target=work,daemon=True).start()

    def set_users(self,users):
        self.users=users
        self.populate_users()

    def populate_users(self):
        if not hasattr(self,"user_tree"):return
        self.user_tree.delete(*self.user_tree.get_children())
        for u in self.users:
            self.user_tree.insert("", "end", values=(u["id"],u["username"],u["role"],u["created_at"]))

    def selected_user_id(self):
        item=self.user_tree.selection()
        if not item:
            messagebox.showinfo(APP,"Select a user first.",parent=self);return None
        return int(self.user_tree.item(item[0],"values")[0])

    def create_user(self):
        r=self.api.request("POST","/api/users",{"username":self.new_user.get().strip(),
                                               "password":self.new_pass.get(),
                                               "role":self.new_role.get()})
        if r.get("ok"):
            self.new_user.delete(0,"end");self.new_pass.delete(0,"end");self.refresh_users()
        else: messagebox.showerror(APP,r.get("error","Could not create user."),parent=self)

    def role(self,role):
        uid=self.selected_user_id()
        if uid is None:return
        r=self.api.request("PATCH",f"/api/users/{uid}/role",{"role":role})
        if r.get("ok"):self.refresh_users()
        else:messagebox.showerror(APP,r.get("error","Could not change role."),parent=self)

    def delete_user(self):
        uid=self.selected_user_id()
        if uid is None:return
        if messagebox.askyesno(APP,"Delete this account?",parent=self):
            r=self.api.request("DELETE",f"/api/users/{uid}")
            if r.get("ok"):self.refresh_users()
            else:messagebox.showerror(APP,r.get("error","Could not delete user."),parent=self)

if __name__ == "__main__":
    Login().mainloop()
