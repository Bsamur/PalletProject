import streamlit as st
import math
import plotly.graph_objects as go
import pandas as pd
import re

# --- 0. YAPILANDIRMA ---
st.set_page_config(page_title="Pro-Alu ERP V89", layout="wide")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🏭 Pro-Alu ERP Sistemine Giriş</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        if st.button("Sisteme Giriş Yap (Yetkili)", use_container_width=True):
            st.session_state.logged_in = True
            st.rerun()
    st.stop() 

# --- 1. YARDIMCI FONKSİYONLAR ---
def create_3d_box(x, y, z, dx, dy, dz, color, name, opacity=0.9):
    return go.Mesh3d(
        x=[x, x+dx, x+dx, x, x, x+dx, x+dx, x], y=[y, y, y+dy, y+dy, y, y, y+dy, y+dy], z=[z, z, z, z, z+dz, z+dz, z+dz, z+dz],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, name=name, showlegend=False, flatshading=True
    )

def parse_pdf(file):
    data = {"w": 0.0, "h": 0.0, "gramaj": 0.0}
    if file is None: return data
    try:
        import pdfplumber
        with pdfplumber.open(file) as pdf:
            text = " ".join([page.extract_text() or "" for page in pdf.pages])
        w_m = re.search(r'(W|Genişlik|Gen)[^\d]*(\d{2,4})', text, re.IGNORECASE)
        h_m = re.search(r'(H|Yükseklik|Yuk)[^\d]*(\d{2,4})', text, re.IGNORECASE)
        gr_m = re.search(r'(\d+[,.]?\d*)\s*(gr/m|kg/m)', text, re.IGNORECASE)
        if w_m: data["w"] = float(w_m.group(2))
        if h_m: data["h"] = float(h_m.group(2))
        if gr_m: data["gramaj"] = float(gr_m.group(1).replace(',', '.'))
    except: pass
    return data

# --- ANA MENÜ ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2897/2897832.png", width=80)
menu = st.sidebar.radio("ERP Modülleri", ["⚙️ Üretim & Paketleme", "🚛 Tır & Sevkiyat Dizilimi"])

# --- MODÜL 1: ÜRETİM VE AKILLI PAKETLEME ---
if menu == "⚙️ Üretim & Paketleme":
    st.header("Yeni Üretim Emri & Akıllı Ambalaj")
    
    col_geo, col_pack, col_pal = st.columns(3)
    
    with col_geo:
        st.subheader("1. Profil & Sipariş")
        siparis_no = st.text_input("Sipariş No", value="SIP-001")
        toplam_siparis_adedi = st.number_input("Toplam Sipariş Adedi (Profil)", min_value=1, value=5000)
        
        c_tip, c_alasim = st.columns(2)
        profil_tipi = c_tip.selectbox("Profil Tipi", ["Özel Profil", "Kutu Profil", "Boru", "L Profil", "Dolu Mil"])
        alasim = c_alasim.selectbox("Alaşım", ["6060-35", "6060-40", "6063-T5"])
        
        # MATEMATİKSEL KUSURSUZ GRAMAJ HESAPLAMALARI
        if profil_tipi == "Özel Profil":
            u_file = st.file_uploader("Teknik Resim Yükle (PDF)", type=["pdf"])
            parsed_data = parse_pdf(u_file)
            if u_file: st.success("📄 PDF verisi okundu.")
            
            p_w = st.number_input("Dış Genişlik W (mm)", min_value=0.01, value=parsed_data["w"] if parsed_data["w"] > 0 else 50.0)
            p_h = st.number_input("Dış Yükseklik H (mm)", min_value=0.01, value=parsed_data["h"] if parsed_data["h"] > 0 else 30.0)
            gramaj_gr = st.number_input("Ağırlık (gr/mt) [Resimden]", min_value=0.01, value=parsed_data["gramaj"] if parsed_data["gramaj"] > 0 else 1250.0)
            gramaj_kg_m = gramaj_gr / 1000 
            renk = "purple"
            
        elif profil_tipi == "Kutu Profil":
            p_w = st.number_input("Genişlik W (mm)", min_value=0.01, value=50.0)
            p_h = st.number_input("Yükseklik H (mm)", min_value=0.01, value=30.0)
            t = st.number_input("Et Kalınlığı t (mm)", min_value=0.01, value=1.5)
            # Matematiksel Güvenlik: Et kalınlığı hiçbir zaman iç boşluğu negatif yapamaz
            t_eff = min(t, p_w/2, p_h/2)
            alan_mm2 = (p_w * p_h) - ((p_w - 2*t_eff) * (p_h - 2*t_eff))
            gramaj_kg_m = alan_mm2 * 0.00271
            renk = "royalblue"
            
        elif profil_tipi == "Boru":
            p_w = st.number_input("Dış Çap Ø (mm)", min_value=0.01, value=40.0)
            p_h = p_w 
            t = st.number_input("Et Kalınlığı t (mm)", min_value=0.01, value=2.0)
            t_eff = min(t, p_w/2)
            alan_mm2 = (math.pi * (p_w/2)**2) - (math.pi * ((p_w/2) - t_eff)**2)
            gramaj_kg_m = alan_mm2 * 0.00271
            renk = "silver"
            
        elif profil_tipi == "L Profil":
            p_w = st.number_input("Genişlik W (mm)", min_value=0.01, value=40.0)
            p_h = st.number_input("Yükseklik H (mm)", min_value=0.01, value=40.0)
            t = st.number_input("Et Kalınlığı t (mm)", min_value=0.01, value=3.0)
            t_eff = min(t, p_w, p_h)
            alan_mm2 = (p_w * t_eff) + ((p_h - t_eff) * t_eff)
            gramaj_kg_m = alan_mm2 * 0.00271
            renk = "forestgreen"
            
        elif profil_tipi == "Dolu Mil":
            p_w = st.number_input("Çap Ø (mm)", min_value=0.01, value=20.0)
            p_h = p_w
            alan_mm2 = math.pi * (p_w/2)**2
            gramaj_kg_m = alan_mm2 * 0.00271
            renk = "darkgray"

        st.info(f"⚖️ **Kullanılacak Birim Ağırlık:** {gramaj_kg_m:.3f} kg/mt\n\n*(Not: R=0 keskin köşe ve Yoğunluk: 2.71 alınmıştır)*")
        kesim_boyu = st.number_input("Kesim Boyu (mm)", min_value=0.01, value=6000.0)

    with col_pack:
        st.subheader("2. Paket (Bağ) Mantığı")
        
        if profil_tipi == "Özel Profil":
            bag_ici_adet = st.number_input("Bağ/Paket İçi Toplam Profil Adedi", min_value=1, value=20)
            bag_w = st.number_input("Bağ Dış Genişliği (mm)", min_value=0.01, value=float(p_w * 5))
            bag_h = st.number_input("Bağ Dış Yüksekliği (mm)", min_value=0.01, value=float(p_h * 4))
        elif profil_tipi == "L Profil":
            eff_w = p_w
            bag_yan_yana = st.number_input("Bağ (Yan Yana Çift)", min_value=1, value=5) * 2
            bag_ust_uste = st.number_input("Bağ (Üst Üste)", min_value=1, value=4)
            bag_ici_adet = bag_yan_yana * bag_ust_uste
            bag_w = (bag_yan_yana / 2) * eff_w
            bag_h = bag_ust_uste * p_h
        elif profil_tipi == "Boru" or profil_tipi == "Dolu Mil":
            bag_yan_yana = st.number_input("Bağ Tabanındaki Profil", min_value=1, value=5)
            bag_ust_uste = st.number_input("Üst Üste Sıra", min_value=1, value=4)
            bag_ici_adet = bag_yan_yana * bag_ust_uste - (bag_ust_uste//2) 
            bag_w = bag_yan_yana * p_w
            bag_h = p_w + (bag_ust_uste - 1) * (p_w * 0.866)
        else: 
            bag_yan_yana = st.number_input("Bağ (Yan Yana)", min_value=1, value=6)
            bag_ust_uste = st.number_input("Bağ (Üst Üste)", min_value=1, value=4)
            bag_ici_adet = bag_yan_yana * bag_ust_uste
            bag_w = bag_yan_yana * p_w
            bag_h = bag_ust_uste * p_h

        st.write(f"**Bağ İçi:** {bag_ici_adet} Adet | **Ebat:** {bag_w:.1f}x{bag_h:.1f} mm")
        ara_katman = st.checkbox("Ara Katman Karton", value=True)
        katman_t = 2.0 if ara_katman else 0.0

    with col_pal:
        st.subheader("3. Palet ve Otomasyon")
        # LİMİTLER KALDIRILDI (Özel Palet Yapılabilir)
        palet_w = st.number_input("Palet Genişliği (mm)", min_value=0.01, value=1000.0)
        palet_l = st.number_input("Palet Uzunluğu (mm)", min_value=0.01, value=float(max(0.01, kesim_boyu)))
        palet_max_h = st.number_input("İstenen Max İstif Yüksekliği (mm)", min_value=0.01, value=1200.0)
        alt_ahsap = st.number_input("Ahşap Palet Kalınlığı (mm)", min_value=0.0, value=140.0)
        
        fit_x = max(1, int(palet_w // bag_w))
        fit_z = max(1, int((palet_max_h - alt_ahsap) // (bag_h + katman_t)))
        palet_ici_profil = fit_x * fit_z * bag_ici_adet
        palet_agirlik = (palet_ici_profil * (kesim_boyu/1000) * gramaj_kg_m) + 25.0 
        
        otomatik_palet = math.ceil(toplam_siparis_adedi / max(1, palet_ici_profil))
        
        st.write(f"📦 **1 Paletteki Profil:** {palet_ici_profil} Adet")
        st.write(f"⚖️ **1 Palet Brüt:** {palet_agirlik:.1f} kg")

        uretilecek_palet = st.number_input("Üretilecek/Sevk Edilecek Palet", min_value=1, value=otomatik_palet)

        if st.button("🛒 Tıra Yüklemek İçin Sıraya Al", type="primary", use_container_width=True):
            st.session_state.cart.append({
                "siparis": siparis_no, "alasim": alasim, "tip": profil_tipi, 
                "palet_adet": uretilecek_palet, "adet_profil": palet_ici_profil * uretilecek_palet,
                "p_w": palet_w, "p_l": palet_l, "p_h": alt_ahsap + (fit_z * (bag_h + katman_t)),
                "agirlik": palet_agirlik, "renk": renk
            })
            st.success(f"{uretilecek_palet} Palet listeye eklendi!")


# --- MODÜL 2: TIR & SEVKİYAT SİMÜLASYONU VE EDİTÖR ---
elif menu == "🚛 Tır & Sevkiyat Dizilimi":
    st.header("Sevkiyat Yönetimi ve Yükleme Planı")
    
    if not st.session_state.cart:
        st.warning("Sevkiyat listesi boş. 'Üretim' sekmesinden sipariş ekleyin.")
    else:
        st.subheader("📋 Aktif Sevkiyat Listesi")
        edited_df = st.data_editor(
            pd.DataFrame(st.session_state.cart),
            num_rows="dynamic", 
            use_container_width=True,
            key="cart_editor"
        )
        st.session_state.cart = edited_df.to_dict('records')
        total_tonnage = (edited_df['palet_adet'] * edited_df['agirlik']).sum() / 1000
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Yük Ağırlığı", f"{total_tonnage:.2f} Ton", delta="Max 24 Ton" if total_tonnage > 24 else "Uygun", delta_color="inverse" if total_tonnage > 24 else "normal")
        c2.metric("Toplam Palet", int(edited_df['palet_adet'].sum()))
        c3.metric("Toplam Profil Adedi", int(edited_df['adet_profil'].sum()))

        st.divider()

        col_truck, col_list = st.columns([2, 1])

        with col_truck:
            st.write("🚚 **3D Dorse Yerleşim Planı** (Max Tavan Yüksekliği: 2600 mm)")
            
            # FİZİKSEL BİLGİLENDİRME NOTU
            st.info("💡 **Bilgi:** 6 metrelik paletler yüklendiğinde, 13.6 metrelik dorseye peş peşe en fazla 2 sıra sığar (12m). Kalan 1.6 metrelik arka boşluğa sığamayacağı için görselde arka taraf boşluklu kalabilir. Bu matematiksel bir zorunluluktur.")
            
            t_w, t_l, t_h = 2450.0, 13600.0, 2600.0
            
            fig_truck = go.Figure()
            fig_truck.add_trace(create_3d_box(0, 0, 0, t_w, t_l, t_h, 'rgba(150,150,150,0.1)', 'Dorse'))
            
            cur_x, cur_y, row_max_l, sigmayan_palet = 0.0, 0.0, 0.0, 0
            
            for idx, row in edited_df.iterrows():
                kalan_palet = int(row['palet_adet'])
                p_w, p_l, p_h = float(row['p_w']), float(row['p_l']), float(row['p_h'])
                
                # FİZİKSEL AŞIM KONTROLÜ (GÜVENLİK DUVARI)
                if p_h > t_h or p_w > t_w or p_l > t_l:
                    sigmayan_palet += kalan_palet
                    continue 
                
                while kalan_palet > 0:
                    # Yeni palet yanyana sığmıyorsa Y ekseninde (uzunlamasına) yeni sıraya geç
                    if cur_x + p_w > t_w:
                        cur_x = 0
                        cur_y += row_max_l + 20 # 20mm tolerans boşluğu
                        row_max_l = 0

                    # Yeni sıraya geçildiğinde dorse uzunluğunu aşıyor mu?
                    if cur_y + p_l > t_l:
                        sigmayan_palet += kalan_palet
                        break 
                    
                    # Double Stacking Kontrolü
                    if kalan_palet >= 2 and (p_h * 2) <= t_h:
                        fig_truck.add_trace(create_3d_box(cur_x, cur_y, 0, p_w, p_l, p_h, row['renk'], f"{row['siparis']} (Alt)", 1.0))
                        fig_truck.add_trace(create_3d_box(cur_x, cur_y, p_h, p_w, p_l, p_h, row['renk'], f"{row['siparis']} (Üst)", 0.8))
                        kalan_palet -= 2
                    else:
                        fig_truck.add_trace(create_3d_box(cur_x, cur_y, 0, p_w, p_l, p_h, row['renk'], row['siparis'], 1.0))
                        kalan_palet -= 1
                    
                    row_max_l = max(row_max_l, p_l)
                    cur_x += p_w
                        
            if sigmayan_palet > 0:
                st.error(f"⚠️ Dorse Uzunluğu veya Yüksekliği Doldu! Tıra sığmayan {int(sigmayan_palet)} adet palet depoda kaldı.")
            else:
                st.success("✅ Tüm paletler araca yerleşti.")
                
            fig_truck.update_layout(scene=dict(aspectmode='data'), height=650, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_truck, use_container_width=True)

        with col_list:
            st.subheader("📄 Packing List")
            ceki_df = edited_df[['siparis', 'alasim', 'tip', 'palet_adet', 'adet_profil', 'agirlik']].copy()
            ceki_df.columns = ['Sipariş No', 'Alaşım', 'Profil Tipi', 'Palet Sayısı', 'Toplam Adet', 'Birim Palet (kg)']
            ceki_df['Toplam Ağırlık (kg)'] = ceki_df['Palet Sayısı'] * ceki_df['Birim Palet (kg)']
            
            st.dataframe(ceki_df, use_container_width=True)
            
            csv_data = ceki_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 Çeki Listesini İndir (Excel)",
                data=csv_data,
                file_name="Packing_List_ProAlu.csv",
                mime="text/csv"
            )
            
            st.divider()
            if st.button("🗑️ Tüm Sevkiyatı Sıfırla", type="primary"):
                st.session_state.cart = []
                st.rerun()