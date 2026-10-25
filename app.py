import streamlit as st
import pandas as pd
import numpy as np
import joblib
import sqlite3
import hashlib
from datetime import datetime

# --- 1. KHỞI TẠO CƠ SỞ DỮ LIỆU SQLITE ---
def init_db():
    conn = sqlite3.connect('medical_cloud.db')
    cursor = conn.cursor()
    
    # Bảng Cơ sở y tế
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS medical_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            center_name TEXT UNIQUE,
            center_code TEXT
        )
    ''')
    
    # Bảng Cán bộ y tế (User)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            center_id INTEGER,
            FOREIGN KEY (center_id) REFERENCES medical_centers (id)
        )
    ''')
    
    # Bảng Lịch sử sàng lọc đa bệnh lý (Có phân quyền theo center_id)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS screenings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            center_id INTEGER,
            username TEXT,
            patient_code TEXT,
            disease_type TEXT,
            risk_result TEXT,
            timestamp TEXT,
            FOREIGN KEY (center_id) REFERENCES medical_centers (id)
        )
    ''')
    
    # Thêm dữ liệu mẫu cơ sở y tế nếu chưa có
    cursor.execute("SELECT COUNT(*) FROM medical_centers")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO medical_centers (center_name, center_code) VALUES ('Bệnh viện Đa khoa Xanh Pôn', 'XP01')")
        cursor.execute("INSERT INTO medical_centers (center_name, center_code) VALUES ('Bệnh viện Bạch Mai', 'BM02')")
        # Tài khoản mẫu: admin / 123456 thuộc viện XP01 (center_id = 1)
        hashed_pw = hashlib.sha256("123456".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, center_id) VALUES ('admin_xanhpon', ?, 1)", (hashed_pw,))
        conn.commit()
        
    conn.close()

init_db()

# --- 2. GIAO DIỆN ĐĂNG NHẬP & PHÂN QUYỀN ---
st.set_page_config(page_title="Hệ thống Sàng lọc Đa bệnh lý Cloud", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ""
    st.session_state['center_id'] = None
    st.session_state['center_name'] = ""

if not st.session_state['logged_in']:
    st.title("🏥 Đăng nhập Hệ thống Sàng lọc Y tế Cloud")
    st.markdown("Hệ thống hỗ trợ sàng lọc đa bệnh lý phục vụ đa cơ sở y tế.")
    
    with st.form("login_form"):
        username = st.text_input("Tên đăng nhập")
        password = st.text_input("Mật khẩu", type="password")
        submit = st.form_submit_button("Đăng nhập")
        
        if submit:
            conn = sqlite3.connect('medical_cloud.db')
            cursor = conn.cursor()
            hashed_pw = hashlib.sha256(password.encode()).hexdigest()
            cursor.execute('''
                SELECT u.id, u.username, u.center_id, c.center_name 
                FROM users u 
                JOIN medical_centers c ON u.center_id = c.id 
                WHERE u.username = ? AND u.password = ?
            ''', (username, hashed_pw))
            user = cursor.fetchone()
            conn.close()
            
            if user:
                st.session_state['logged_in'] = True
                st.session_state['username'] = user[1]
                st.session_state['center_id'] = user[2]
                st.session_state['center_name'] = user[3]
                st.success("Đăng nhập thành công!")
                st.rerun()
            else:
                st.error("Sai tên đăng nhập hoặc mật khẩu!")
else:
    # --- 3. GIAO DIỆN CHÍNH SAU KHI ĐĂNG NHẬP ---
    st.sidebar.title(f"🏢 {st.session_state['center_name']}")
    st.sidebar.write(f"Cán bộ: **{st.session_state['username']}**")
    menu = st.sidebar.selectbox("Chức năng", ["Sàng lọc Bệnh lý mới", "Lịch sử Sàng lọc của Cơ sở"])
    
    if st.sidebar.button("Đăng xuất"):
        st.session_state['logged_in'] = False
        st.rerun()
        
    if menu == "Sàng lọc Bệnh lý mới":
        st.title("🩺 Biểu mẫu Sàng lọc Nguy cơ Đa bệnh lý")
        
        patient_code = st.text_input("Mã định danh ẩn danh bệnh nhân (Ví dụ: BN-2026-8821)")
        disease_choice = st.selectbox("Chọn loại bệnh cần sàng lọc", ["Bệnh Tim mạch (Heart Disease)", "Bệnh Tiểu đường (Diabetes)"])
        
        if disease_choice == "Bệnh Tim mạch (Heart Disease)":
            st.subheader("Nhập chỉ số lâm sàng Tim mạch")
            col1, col2, col3 = st.columns(3)
            with col1:
                age = st.number_input("Tuổi", 20, 100, 50)
                sex = st.selectbox("Giới tính", [1, 0], format_func=lambda x: "Nam" if x==1 else "Nữ")
                cp = st.selectbox("Loại đau ngực (cp)", [1, 2, 3, 4])
                trestbps = st.number_input("Huyết áp lúc nghỉ (trestbps)", 90, 200, 120)
                chol = st.number_input("Cholesterol", 100, 600, 200)
            with col2:
                fbs = st.selectbox("Đường huyết lúc đói > 120 mg/dl (fbs)", [0, 1])
                restecg = st.selectbox("Điện tâm đồ (restecg)", [0, 1, 2])
                thalach = st.number_input("Nhịp tim tối đa đạt được (thalach)", 60, 220, 150)
                exang = st.selectbox("Đau thắt ngực khi gắng sức (exang)", [0, 1])
            with col3:
                oldpeak = st.number_input("ST depression (oldpeak)", 0.0, 6.0, 1.0)
                slope = st.selectbox("Độ dốc đoạn ST (slope)", [1, 2, 3])
                ca = st.number_input("Số mạch máu chính (ca)", 0, 3, 0)
                thal = st.selectbox("Thalassemia (thal)", [3, 6, 7])
                
            if st.button("Phân tích Nguy cơ Tim mạch"):
                try:
                    model = joblib.load('heart_model.pkl')
                    scaler = joblib.load('heart_scaler.pkl')
                    
                    input_data = np.array([[age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal]])
                    input_scaled = scaler.transform(input_data)
                    prediction = model.predict(input_scaled)[0]
                    prob = model.predict_proba(input_scaled)[0][1]
                    
                    risk_str = f"Nguy cơ Cao ({prob*100:.1f}%)" if prediction == 1 else f"Nguy cơ Thấp ({prob*100:.1f}%)"
                    
                    if prediction == 1:
                        st.error(f"Kết quả: {risk_str} - Cần chuyển tuyến chuyên khoa kiểm tra sâu hơn!")
                    else:
                        st.success(f"Kết quả: {risk_str} - Bệnh nhân ở ngưỡng an toàn.")
                        
                    # Lưu vào Database với đúng center_id của cán bộ
                    conn = sqlite3.connect('medical_cloud.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO screenings (center_id, username, patient_code, disease_type, risk_result, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (st.session_state['center_id'], st.session_state['username'], patient_code, "Tim mạch", risk_str, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    st.warning("Chưa tìm thấy file mô hình `heart_model.pkl`. Hãy chạy code huấn luyện trên Colab và tải file về thư mục dự án trước.")
                    
        elif disease_choice == "Bệnh Tiểu đường (Diabetes)":
            st.subheader("Nhập chỉ số lâm sàng Tiểu đường")
            col1, col2 = st.columns(2)
            with col1:
                pregnancies = st.number_input("Số lần mang thai (Pregnancies)", 0, 20, 0)
                glucose = st.number_input("Nồng độ Glucose", 0, 200, 100)
                bp = st.number_input("Huyết áp (BloodPressure)", 0, 150, 70)
                skin = st.number_input("Độ dày nếp gấp da (SkinThickness)", 0, 100, 20)
            with col2:
                insulin = st.number_input("Insulin", 0, 900, 80)
                bmi = st.number_input("Chỉ số BMI", 0.0, 70.0, 25.0)
                dpf = st.number_input("Hàm số di truyền tiểu đường (DPF)", 0.0, 3.0, 0.5)
                age_dia = st.number_input("Tuổi (Age)", 10, 100, 30)
                
            if st.button("Phân tích Nguy cơ Tiểu đường"):
                try:
                    model_dia = joblib.load('diabetes_model.pkl')
                    scaler_dia = joblib.load('diabetes_scaler.pkl')
                    
                    input_dia = np.array([[pregnancies, glucose, bp, skin, insulin, bmi, dpf, age_dia]])
                    input_dia_scaled = scaler_dia.transform(input_dia)
                    pred_dia = model_dia.predict(input_dia_scaled)[0]
                    prob_dia = model_dia.predict_proba(input_dia_scaled)[0][1]
                    
                    risk_str_dia = f"Nguy cơ Cao ({prob_dia*100:.1f}%)" if pred_dia == 1 else f"Nguy cơ Thấp ({prob_dia*100:.1f}%)"
                    
                    if pred_dia == 1:
                        st.error(f"Kết quả: {risk_str_dia} - Cần xét nghiệm đường huyết lúc đói / HbA1c.")
                    else:
                        st.success(f"Kết quả: {risk_str_dia} - Chỉ số bình thường.")
                        
                    # Lưu Database
                    conn = sqlite3.connect('medical_cloud.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO screenings (center_id, username, patient_code, disease_type, risk_result, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (st.session_state['center_id'], st.session_state['username'], patient_code, "Tiểu đường", risk_str_dia, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    st.warning("Chưa tìm thấy file mô hình `diabetes_model.pkl`.")

    elif menu == "Lịch sử Sàng lọc của Cơ sở":
        st.title(f"📋 Lịch sử Sàng lọc - {st.session_state['center_name']}")
        st.write("Danh sách các ca sàng lọc được thực hiện bởi các cán bộ trong cơ sở y tế của bạn (Bảo mật đa tenant tuyệt đối).")
        
        conn = sqlite3.connect('medical_cloud.db')
        query = '''
            SELECT patient_code, disease_type, risk_result, username, timestamp 
            FROM screenings 
            WHERE center_id = ? 
            ORDER BY id DESC
        '''
        df_history = pd.read_sql(query, conn, params=(st.session_state['center_id'],))
        conn.close()
        
        if not df_history.empty:
            st.dataframe(df_history, use_container_width=True)
        else:
            st.info("Chưa có lịch sử sàng lọc nào được ghi nhận cho cơ sở y tế này.")