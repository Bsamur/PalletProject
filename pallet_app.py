import streamlit as st
import math
import plotly.graph_objects as go
from fpdf import FPDF
import datetime
import pdfplumber
import re

# --- 1. YARDIMCI FONKSİYONLAR ---
def tr_fix(text):
    if text is None: return ""
    mapping = {'İ': 'I', 'ı': 'i', 'Ş': 'S', 'ş': 's', 'Ğ': 'G', 'ğ': 'g', 'Ü': 'U', 'ü': 'u', 'Ö': 'O', 'ö': 'o', 'Ç': 'C', 'ç': 'c'}
    for tr, eng in mapping.items(): text = str(text).replace(tr, eng)
    return text

def smart_pdf_parser(file):
    """PDF içinden Boy ve Gramaj verilerini yakalar."""
    data = {"siparis": "YENI-LOT", "boy": 6000.0, "gramaj": 1250.0}
    try:
        with pdfplumber.open(file) as pdf:
            text = " ".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            # Boy Yakalama
            boy_m = re.search(r'boy[^\d]*(\d{3,5})', text, re.IGNORECASE)
            if boy_m: data["boy"] = float(boy_m.group(1))
            # Gramaj Yakalama
            gr_m = re.search(r'(gr/m|gramaj)[^\d]*(\d{2,5})', text, re.IGNORECASE)
            if gr_m: data["gramaj"] = float(gr_m.group(2))
            # Sipariş No
            sip_m = re.search(r'(siparis|lot|re)[-\s]*([a-zA-Z0-9]+)', text, re.IGNORECASE)
            if sip_m: data["siparis"] = sip_m.group(2).upper()
    except: pass
    return data

st.set_page_config(page_title="Pro-Alu V55 | Akıllı Sevkiyat Merkezi", layout="wide")
st.title("🚀 Pro-Alu V55: Akıllı Analiz & Dorse Yerleşim Sistemi")

# --- 2. VERİ KAYNAĞI ---
with st.container(border=True):
    u_file = st.file_uploader("📂 Teknik Resim veya Sipariş PDF'i Yükle", type=["pdf", "png", "jpg"])
    extracted = smart_pdf_parser(u_file) if u_file else {"siparis": "", "boy": 6000.0, "gramaj": 1250.0}

# --- 3. MANUEL REVİZYON VE GİRİŞ FORMU ---
with st.form("main_form"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.subheader("📋 Kimlik")
        musteri = st.text_input("Musteri", "Ornek Alu")
        siparis = st.text_input("Siparis No", extracted["siparis"])
        p_tipi = st.selectbox("Paketleme", ["Standart Baglama", "Kutulu", "Ozel Sandik"])
    
    with c2:
        st.subheader("📐 Profil")
        L_profil = st.number_input("Profil Boyu (mm)", value=extracted["boy"])
        grmt = st.number_input("Metre Agirligi (gr/mt)", value=extracted["gramaj"])
        p_ici = st.number_input("Paket Ici Adet", value=48)
        
    with c3:
        st.subheader("📦 Paket/Kutu")
        p_w = st.number_input("Paket Genisligi (mm)", value=320)
        p_h = st.number_input("Paket Yuksekligi (mm)", value=220)
        p_dara = st.number_input("Paket Darasi (kg)", value=1.5)

    with c4:
        st.subheader("🚛 Palet & Sevk")
        pal_w = st.number_input("Palet Genisligi (mm)", value=1000)
        max_h = st.number_input("Maks. Sevk Yuk. (mm)", value=1250)
        dorse_sec = st.selectbox("Dorse Tipi", ["Tenteli (13.6m)", "Mega (3m Yuksek)", "Frigo"])

    st.divider()
    submit = st.form_submit_button("✅ VERİLERİ ONAYLA VE TÜM SİSTEMİ HESAPLA", use_container_width=True)

# --- 4. MÜHENDİSLİK HESAPLAMALARI ---
# Ağırlıklar
profil_kg = (L_profil / 1000) * (grmt / 1000)
paket_brut = (profil_kg * p_ici) + p_dara

# Palet İçi Dizilim (Tam Kapasite)
yana_p = int(pal_w // (p_w + 2))
kat, top_p, cur_h = 0, 0, 140 # 140mm alt takoz
while (cur_h + p_h) <= max_h:
    kat += 1
    top_p += yana_p
    cur_h += p_h
    if (cur_h + 20 + p_h) <= max_h: cur_h += 20 # 20mm ara takoz
    else: break

palet_brut_kg = (top_p * paket_brut) + (L_profil/1000 * 15) # Palet kereste ağırlığı dahil

# Dorse Yerleşim Analizi
d_l, d_w = (13600, 2450) if "Tenteli" in dorse_sec else (13600, 2480)
yana_palet = int(d_w // pal_w)
arka_arkaya = int(d_l // (L_profil + 100)) # Palet boyu = Profil + 100mm pay
toplam_palet = yana_palet * arka_arkaya
toplam_tonaj = (toplam_palet * palet_brut_kg) / 1000

# --- 5. GÖRSELLEŞTİRME VE SONUÇLAR ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Palet İçi Paket", f"{top_p} Adet", f"{kat} Kat")
m2.metric("Palet Brüt", f"{palet_brut_kg:.1f} kg")
m3.metric("Dorse Kapasite", f"{toplam_palet} Palet")
m4.metric("Toplam Sevk", f"{toplam_tonaj:.2f} Ton")

c_plot, c_info = st.columns([2, 1])

with c_plot:
    fig = go.Figure()
    def add_box(x, y, z, dx, dy, dz, color, name, op=0.8):
        fig.add_trace(go.Mesh3d(x=[x,x+dx,x+dx,x,x,x+dx,x+dx,x], y=[y,y,y+dy,y+dy,y,y,y+dy,y+dy], z=[z,z,z,z,z+dz,z+dz,z+dz,z+dz],
            i=[7,0,0,0,4,4,6,6,4,0,3,2], j=[3,4,1,2,5,6,5,2,0,1,6,3], k=[0,7,2,3,6,7,1,1,5,5,7,6], color=color, opacity=op, name=name))

    # Dorse Şeffaf Çizim
    add_box(0, 0, 0, d_w, d_l, 2700, 'lightgray', 'Dorse', 0.1)
    
    # Paletleri Dorseye Dizme
    p_boy = L_profil + 100
    for r in range(arka_arkaya):
        for c in range(yana_palet):
            add_box(c*pal_w, r*p_boy, 0, pal_w, p_boy, cur_h, 'royalblue', 'Palet')

    fig.update_layout(scene=dict(aspectmode='data'), height=600, margin=dict(l=0,r=0,b=0,t=0))
    st.plotly_chart(fig, use_container_width=True)

with c_info:
    st.info(f"**Lojistik Notu:** Bu sevkiyat için {toplam_palet} adet palet planlanmıştır. Dorse tabanında {yana_palet} sıra yan yana dizilim yapılmıştır.")
    if st.button("📑 DETAYLI SEVK RAPORU (PDF)"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, tr_fix(f"SEVKIYAT ANALIZI: {siparis}"), 0, 1, 'C')
        pdf.set_font("Arial", "", 12)
        pdf.ln(10)
        res = [["Musteri", musteri], ["Profil Boyu", f"{L_profil} mm"], ["Gramaj", f"{grmt} gr/mt"], 
               ["Palet Sayisi", f"{toplam_palet} Adet"], ["Toplam Tonaj", f"{toplam_tonaj:.2f} Ton"]]
        for k, v in res:
            pdf.cell(90, 10, tr_fix(k), 1); pdf.cell(100, 10, tr_fix(v), 1, 1)
        st.download_button("📥 Raporu İndir", data=bytes(pdf.output()), file_name=f"Analiz_{siparis}.pdf")