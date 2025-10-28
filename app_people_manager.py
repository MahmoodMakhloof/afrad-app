import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import ttkbootstrap as ttkb
import sqlite3
import pandas as pd
import os, platform, tempfile, subprocess
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from constants import ranks, reason_for_entitlement_lastyear, non_reasons,initial_entities,DB_NAME
# =========================================================
# إعداد قاعدة البيانات
# =========================================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS entities (
        code TEXT PRIMARY KEY,
        name TEXT
    )''')
    

    for code, name in initial_entities:
        c.execute("INSERT OR IGNORE INTO entities (code, name) VALUES (?, ?)", (code, name))
    
    c.execute('''CREATE TABLE IF NOT EXISTS people (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_number TEXT,
        rank TEXT,
        people_name TEXT,
        entities TEXT,
        reason_for_entitlement TEXT,
        assigned_work TEXT,
        reason_for_entitlement_lastyear TEXT,
        non_reason_for_entitlement_lastyear TEXT,
        deputed_from TEXT
    )''')
    conn.commit()
    conn.close()

# =========================================================
# دوال التعامل مع البيانات
# =========================================================
def refresh_treeview():
    for row in tree.get_children():
        tree.delete(row)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM people")
    rows = c.fetchall()
    for row in rows:
        tree.insert("", tk.END, values=row)
    conn.close()
    # تحديث العداد
    count_var.set(f"🔢 عدد السجلات الحالية: {len(rows)}")

def add_record():
    data = []
    name_value = ""
    id_number_value = ""

    for i, field in enumerate(fields):
        if field == "الجهة":
            data.append(current_entity)
        else:
            value = entry_widgets[i].get().strip()
            data.append(value)
            if field == "الاسم":
                name_value = value
            if field == "رقم الشرطة":
                id_number_value = value

    # تحقق من أن الاسم رباعي
    if len(name_value.split()) < 4:
        messagebox.showwarning("تنبيه", "الاسم يجب أن يكون رباعيًا (يتكون من 4 كلمات على الأقل).")
        return

    # تحقق من أن رقم الشرطة غير فارغ
    if not id_number_value:
        messagebox.showwarning("تنبيه", "من فضلك أدخل رقم الشرطة.")
        return

    # تحقق من أن رقم الشرطة غير مكرر
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM people WHERE id_number = ?", (id_number_value,))
    if c.fetchone()[0] > 0:
        conn.close()
        messagebox.showerror("خطأ", "رقم الشرطة موجود بالفعل ⚠️")
        return

    # المنتدب اختياري
    deputed_value = deputed_from_var.get() if deputed_check_var.get() else ""
    data.append(deputed_value)

    # تحقق من الحقول الإلزامية (باستثناء المنتدب)
    if not all(data[:-1]):
        messagebox.showwarning("تنبيه", "من فضلك املأ جميع الحقول المطلوبة.")
        conn.close()
        return

    # حفظ البيانات
    c.execute('''INSERT INTO people 
        (id_number, rank, people_name, entities, reason_for_entitlement,
        assigned_work, reason_for_entitlement_lastyear, non_reason_for_entitlement_lastyear, deputed_from)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', data)
    conn.commit()
    conn.close()

    refresh_treeview()
    clear_entries()
    messagebox.showinfo("تم", "تمت الإضافة بنجاح ✅")

def update_record():
    selected = tree.focus()
    if not selected:
        messagebox.showwarning("تنبيه", "من فضلك اختر سجل لتعديله.")
        return
    values = tree.item(selected, "values")
    record_id = values[0]
    data = []
    name_value = ""

    for i, field in enumerate(fields):
        if field == "الجهة":
            data.append(current_entity)
        else:
            value = entry_widgets[i].get().strip()
            data.append(value)
            if field == "الاسم":
                name_value = value

    # تحقق من أن الاسم رباعي
    if len(name_value.split()) < 4:
        messagebox.showwarning("تنبيه", "الاسم يجب أن يكون رباعيًا (يتكون من 4 كلمات على الأقل).")
        return

    deputed_value = deputed_from_var.get() if deputed_check_var.get() else ""
    data.append(deputed_value)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''UPDATE people SET
        id_number=?, rank=?, people_name=?, entities=?, reason_for_entitlement=?,
        assigned_work=?, reason_for_entitlement_lastyear=?, non_reason_for_entitlement_lastyear=?, deputed_from=?
        WHERE id=?''', data + [record_id])
    conn.commit()
    conn.close()
    refresh_treeview()
    clear_entries()
    messagebox.showinfo("تم", "تم تعديل السجل بنجاح ✏️")

def delete_record():
    selected = tree.focus()
    if not selected:
        messagebox.showwarning("تنبيه", "من فضلك اختر سجل لحذفه.")
        return
    values = tree.item(selected, "values")
    record_id = values[0]
    if messagebox.askyesno("تأكيد", "هل أنت متأكد من الحذف؟"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM people WHERE id=?", (record_id,))
        conn.commit()
        conn.close()
        refresh_treeview()
        messagebox.showinfo("تم", "تم حذف السجل 🗑️")

def clear_entries():
    for i, widget in enumerate(entry_widgets):
        field = fields[i]
        if field == "الجهة":
            continue
        if isinstance(widget, ttk.Combobox):
            widget.set("")
        else:
            widget.delete(0, tk.END)
    deputed_check_var.set(False)
    deputed_from_var.set("")

def on_tree_select(event):
    selected = tree.focus()
    if selected:
        values = tree.item(selected, "values")[1:]
        for i, field in enumerate(fields):
            if field == "الجهة":
                continue
            widget = entry_widgets[i]
            if isinstance(widget, ttk.Combobox):
                widget.set(values[i])
            else:
                widget.delete(0, tk.END)
                widget.insert(0, values[i])
        deputed_value = values[-1] if len(values) > 8 else ""
        deputed_from_var.set(deputed_value)
        deputed_check_var.set(bool(deputed_value))

# =========================================================
# التعامل مع Excel
# =========================================================
def export_to_excel():
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel Files", "*.xlsx")])
    if not file_path:
        return
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM people", conn)
    conn.close()
    df.to_excel(file_path, index=False)
    messagebox.showinfo("تم", "تم تصدير البيانات إلى ملف Excel بنجاح ✅")

def import_from_excel():
    file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
    if not file_path:
        return
    df = pd.read_excel(file_path)
    conn = sqlite3.connect(DB_NAME)
    df.to_sql("people", conn, if_exists="append", index=False)
    conn.close()
    refresh_treeview()
    messagebox.showinfo("تم", "تم استيراد البيانات من ملف Excel ✅")

# =========================================================
# إنشاء PDF بالعربي (مع لوجو + توقيع عربي)
# =========================================================
def generate_pdf(preview=False):
    from arabic_reshaper import reshape
    from bidi.algorithm import get_display
    from reportlab.platypus import Image, Paragraph, Table, TableStyle, Spacer, SimpleDocTemplate
    from reportlab.pdfgen import canvas

    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM people", conn)
    conn.close()

    if df.empty:
        messagebox.showinfo("تنبيه", "لا توجد بيانات للطباعة.")
        return

    font_path = "Amiri-Regular.ttf"
    if not os.path.exists(font_path):
        font_path = "Cairo-Regular.ttf"
    if not os.path.exists(font_path):
        messagebox.showerror("خطأ", "الخط العربي غير موجود بجانب الملف!")
        return

    pdfmetrics.registerFont(TTFont("Arabic", font_path))
    addMapping("Arabic", 0, 0, "Arabic")

    def fix_arabic(text):
        if pd.isna(text):
            return ""
        return get_display(reshape(str(text)))

    columns_map = {
        "id": "م",
        "id_number": "رقم الشرطة",
        "rank": "الدرجة",
        "people_name": "الاسم",
        "entities": "الجهة",
        "reason_for_entitlement": "سبب الاستحقاق",
        "assigned_work": "العمل المسند إليه",
        "reason_for_entitlement_lastyear": "سبب الاستحقاق العام الماضي",
        "non_reason_for_entitlement_lastyear": "سبب عدم الاستحقاق العام الماضي",
        "deputed_from": "منتدب من"
    }

    df = df.rename(columns=columns_map)
    df = df[list(columns_map.values())[::-1]]
    data = [list(map(fix_arabic, df.columns.tolist()))] + df.apply(lambda r: [fix_arabic(x) for x in r], axis=1).tolist()

    temp_path = os.path.join(tempfile.gettempdir(), "people_report.pdf")
    doc = SimpleDocTemplate(temp_path, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    style = styles["Title"]
    style.fontName = "Arabic"

    elements = []

    title = Paragraph(f"<b>{fix_arabic('تقرير الأفراد المستحقين بصرف الملابس المدنية - ' + current_entity)}</b>", style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Arabic'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2E86C1")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.gray),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 40))

    # عدد السجلات
    record_count = len(df)
    count_text = f"إجمالي عدد السجلات: {record_count}"
    count_text_fixed = get_display(reshape(count_text))

    # ========= دوال الطباعة على كل صفحة =========
    def add_page_elements(canv, doc):
        page_num = canv.getPageNumber()
        width, height = landscape(A4)  # مهم جدًا لتحديد الاتجاه الصحيح

        # --- اللوجو أعلى يمين الصفحة ---
        logo_path = "logo.png"
        if os.path.exists(logo_path):
            canv.drawImage(logo_path, width - 80, height - 60, width=60, height=40, mask='auto')

        # --- رقم الصفحة في المنتصف السفلي ---
        text = f"الصفحة {page_num}"
        reshaped_text = get_display(reshape(text))
        canv.setFont("Arabic", 10)
        canv.drawCentredString(width / 2, 20, reshaped_text)

        # --- توقيع "يعتمد" أسفل يسار الصفحة ---
        sign_text = get_display(reshape("يعتمد"))
        canv.setFont("Arabic", 14)
        canv.drawString(50, 40, sign_text)

        # --- لو دي آخر صفحة نضيف عدد السجلات ---
        if page_num == doc.page:
            canv.setFont("Arabic", 12)
            canv.drawCentredString(width / 2, 50, count_text_fixed)

    # بناء التقرير مع الترقيم واللوجو والتوقيع
    doc.build(elements, onFirstPage=add_page_elements, onLaterPages=add_page_elements)

    # فتح أو طباعة
    if preview:
        os.startfile(temp_path) if platform.system() == "Windows" else subprocess.call(["open", temp_path])
    else:
        if platform.system() == "Windows":
            os.startfile(temp_path, "print")
        elif platform.system() == "Darwin":
            subprocess.run(["lp", temp_path])
        else:
            subprocess.run(["xdg-open", temp_path])
        messagebox.showinfo("تم", "تم إرسال التقرير للطباعة 🖨️")




# =========================================================
# شاشة الدخول
# =========================================================
def show_login():
    login_win = ttkb.Toplevel()
    login_win.title("🔑 تسجيل الدخول للجهة")

    window_width = 400
    window_height = 180
    screen_width = login_win.winfo_screenwidth()
    screen_height = login_win.winfo_screenheight()
    x_position = int((screen_width / 2) - (window_width / 2))
    y_position = int((screen_height / 2) - (window_height / 2))
    login_win.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

    login_win.resizable(False, False)
    login_win.attributes("-topmost", True)
    login_win.transient(app)
    login_win.grab_set()

    ttkb.Label(login_win, text="أدخل كود الجهة:", bootstyle="info", font=("Cairo", 12, "bold")).pack(pady=20)
    code_var = tk.StringVar()
    entry_code = ttkb.Entry(login_win, textvariable=code_var, width=30, font=("Cairo", 12))
    entry_code.pack(pady=5)
    entry_code.focus()

    def login_action():
        code = code_var.get().strip()
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT name FROM entities WHERE code=?", (code,))
        row = c.fetchone()
        conn.close()
        if row:
            global current_entity
            current_entity = row[0]
            entity_label_var.set(current_entity)
            login_win.destroy()
        else:
            messagebox.showerror("خطأ", "كود الجهة غير صحيح!")

    ttkb.Button(login_win, text="دخول", bootstyle="success", command=login_action).pack(pady=15)
    login_win.wait_window()

# =========================================================
# الواجهة الرئيسية
# =========================================================
app = ttkb.Window(themename="flatly")
app.title("💿 الملابس المدنية أفراد")
app.geometry("1300x700")

init_db()

fields = [
    "رقم الشرطة", "الدرجة", "الاسم", "الجهة",
    "سبب الاستحقاق", "العمل المسند إليه",
    "سبب الاستحقاق العام الماضي", "سبب عدم الاستحقاق العام الماضي"
]



entry_widgets = []
frame_top = ttkb.Frame(app, padding=10)
frame_top.pack(fill="x")

# ===================== الحقول الأساسية =====================
for i, field in enumerate(fields):
    # تحديد موقع كل Label و Widget بشكل مرن
    row = i // 4 * 2
    col = i % 4

    # إنشاء اللابل
    ttkb.Label(
        frame_top,
        text=field,
        bootstyle="info",
        font=("Cairo", 11, "bold")
    ).grid(row=row, column=col, padx=5, pady=(3, 0), sticky="w")

    # إنشاء عنصر الإدخال المناسب
    if field == "الدرجة":
        widget = ttk.Combobox(frame_top, values=ranks, width=25, state="readonly")

    elif field == "الجهة":
        entity_label_var = tk.StringVar(value="")
        widget = ttkb.Label(
            frame_top,
            textvariable=entity_label_var,
            bootstyle="info",
            width=28,
            font=("Cairo", 25, "bold")
        )

    elif field == "الاسم":
        widget = ttkb.Entry(frame_top, width=35, font=("Cairo", 12))

    elif field == "سبب الاستحقاق العام الماضي":
        widget = ttk.Combobox(frame_top, values=reason_for_entitlement_lastyear, width=25, state="readonly")

    elif field == "سبب عدم الاستحقاق العام الماضي":
        widget = ttk.Combobox(frame_top, values=non_reasons, width=25, state="readonly")

    else:
        widget = ttkb.Entry(frame_top, width=28, font=("Cairo", 11))

    # ترتيب العنصر داخل الشبكة
    widget.grid(row=row + 1, column=col, padx=5, pady=3, sticky="ew")
    entry_widgets.append(widget)

# جعل الأعمدة تتمدد تلقائيًا (Responsive)
for col in range(4):
    frame_top.columnconfigure(col, weight=1)

# ===================== قسم المنتدب =====================
frame_deputed = ttkb.Frame(app, padding=10)
frame_deputed.pack(fill="x")
deputed_check_var = tk.BooleanVar()
deputed_from_var = tk.StringVar()

def toggle_deputed_combo():
    if deputed_check_var.get():
        available_entities = [name for code, name in initial_entities if name != current_entity]
        deputed_combo["values"] = available_entities
        deputed_combo.pack(side="left", padx=10, expand=True, fill="x")
    else:
        deputed_combo.pack_forget()
        deputed_from_var.set("")

ttkb.Checkbutton(
    frame_deputed,
    text="منتدب من",
    variable=deputed_check_var,
    bootstyle="info-round-toggle",
    command=toggle_deputed_combo
).pack(side="left", padx=5)

deputed_combo = ttk.Combobox(
    frame_deputed,
    textvariable=deputed_from_var,
    values=[name for code, name in initial_entities],
    width=40,
    state="readonly",
    font=("Cairo", 11)
)
deputed_combo.pack_forget()

frame_buttons = ttkb.Frame(app, padding=10)
frame_buttons.pack(fill="x")
ttkb.Button(frame_buttons, text="➕ إضافة", bootstyle="success", command=add_record).pack(side="left", padx=5)
ttkb.Button(frame_buttons, text="✏️ تعديل", bootstyle="info", command=update_record).pack(side="left", padx=5)
ttkb.Button(frame_buttons, text="🗑 حذف", bootstyle="danger", command=delete_record).pack(side="left", padx=5)
ttkb.Button(frame_buttons, text="📥 استيراد Excel", bootstyle="warning", command=import_from_excel).pack(side="left", padx=5)
ttkb.Button(frame_buttons, text="📤 تصدير Excel", bootstyle="primary", command=export_to_excel).pack(side="left", padx=5)
ttkb.Button(frame_buttons, text="🧹 مسح الحقول", bootstyle="light", command=clear_entries).pack(side="left", padx=5)

frame_tree = ttkb.Frame(app, padding=10)
frame_tree.pack(fill="both", expand=True)
cols = ["id"] + fields + ["الجهة المنتدب منها"]
tree = ttk.Treeview(frame_tree, columns=cols, show="headings")
for col in cols:
    tree.heading(col, text=col)
    tree.column(col, width=130)
tree.pack(fill="both", expand=True)
tree.bind("<<TreeviewSelect>>", on_tree_select)

count_var = tk.StringVar(value="🔢 عدد السجلات الحالية: 0")
count_label = ttkb.Label(app, textvariable=count_var, bootstyle="info", font=("Cairo", 12, "bold"))
count_label.pack(pady=5)

frame_print = ttkb.Frame(app, padding=10)
frame_print.pack(fill="x")
ttkb.Button(frame_print, text="👁️ استعراض", bootstyle="info", command=lambda: generate_pdf(preview=True)).pack(side="left", padx=5)
ttkb.Button(frame_print, text="🖨️ طباعة", bootstyle="success", command=lambda: generate_pdf(preview=False)).pack(side="left", padx=5)

current_entity = ""
show_login()
refresh_treeview()
app.mainloop()
