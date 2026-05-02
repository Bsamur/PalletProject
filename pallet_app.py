import streamlit as st
import math
import plotly.graph_objects as go
import pandas as pd
import re

# --- 0. YAPILANDIRMA ---
st.set_page_config(page_title="Pro-Alu ERP V93", layout="wide")

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

# --- 1. YARDIMCI 3D FONKSİYONLAR ---
def create_3d_box(x, y, z, dx, dy, dz, color, name, opacity=0.9):
    return go.Mesh3d(
        x=[x, x+dx, x+dx, x, x, x+dx, x+dx, x], y=[y, y, y+dy, y+dy, y, y, y+dy, y+dy], z=[z, z, z, z, z+dz, z+dz, z+dz, z+dz],
        i=[7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2], j=[3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3], k=[0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6],
        color=color, opacity=opacity, name=name, showlegend=False, flatshading=True
    )

def create_3d_cylinder(cx, cy, cz, r, length, color, name, opacity=1.0, yon="Yatay"):
    """Yöne göre yatan veya dik duran pürüzsüz 3D Silindir"""
    x_pts, y_pts, z_pts = [], [], []
    for i in range(24): 
        a = i * (2 * math.pi / 24)
        if yon == "Yatay":
            px, pz = cx + r * math.cos(a), cz + r * math.sin(a)
            x_pts.extend([px, px]); y_pts.extend([cy, cy + length]); z_pts.extend([pz, pz])
        else: # Dikine Tabana Oturan
            px, py = cx + r * math.cos(a), cy + r * math.sin(a)
            x_pts.extend([px, px]); y_pts.extend([py, py]); z_pts.extend([cz, cz + length])
    return go.Mesh3d(x=x_pts, y=y_pts, z=z_pts, alphahull=0, color=color, opacity=opacity, name=name, showlegend=False, flatshading=True)

cam_angle = dict(camera=dict(eye=dict(x=1.6, y=-1.6, z=1.2)))

# --- AKILLI OPTİMİZASYON MOTORU ---
def optimize_bundle(p_w, p_h, shape, limit_x, limit_y):
    """Palet veya İstif sınırlarına göre en uygun matrisi bulur"""
    best_c, best_r, max_total = 1, 1, 0
    max_c = max(2, int(limit_x / p_w)) if p_w > 0 else 1
    max_r = max(2, int(limit_y / p_h)) if p_h > 0 else 1
    
    for c in range(1, max_c + 1):
        for r in range(1, max_r + 1):
            if shape in ["Boru", "Dolu Mil"]:
                b_w = c * p_w
                b_h = p_w + (r - 1) * (p_w * 0.866)
                total_items = (c * r) - (r // 2) 
            elif shape == "L Profil":
                b_w = (c / 2.0) * p_w
                b_h = r * p_h
                total_items = c * r
            else:
                b_w = c * p_w
                b_h = r * p_h
                total_items = c * r
                
            if b_w > 1200 or b_h > 1200: continue # Aşırı devasa bağları engelle
            
            fit_x = int(limit_x // b_w) if b_w > 0 else 0
            fit_y = int(limit_y // b_h) if b_h > 0 else 0
            
            if (fit_x * fit_y * total_items) > max_total:
                max_total = (fit_x * fit_y * total_items)
                best_c, best_r = c, r
                
    return best_c if best_c > 0 else 1, best_r if best_r > 0 else 1

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
    
    col_geo, col_pal, col_pack = st.columns([1.2, 1, 1.2]) 
    
    with col_geo:
        st.subheader("1. Profil & Sipariş")
        siparis_no = st.text_input("Sipariş No", value="SIP-001")
        toplam_siparis_adedi = st.number_input("Toplam Sipariş Adedi", min_value=1, value=5000)
        
        c_tip, c_alasim = st.columns(2)
        profil_tipi = c_tip.selectbox("Profil Tipi", ["Kutu Profil", "Boru", "Özel Profil", "L Profil", "Dolu Mil"])
        alasim = c_alasim.selectbox("Alaşım", ["6060-40", "6060-35", "6063-T5"])
        
        # YENİ EKLENEN ORYANTASYON (YÖN) SEÇENEĞİ
        yon = st.radio("Yerleşim Yönü:", ["Yatay (Standart, Uzunlamasına)", "Dikey (Tabana Oturur, Dikleme)"])
        
        if profil_tipi == "Özel Profil":
            u_file = st.file_uploader("Teknik Resim Yükle (PDF)", type=["pdf"])
            parsed_data = parse_pdf(u_file)
            p_w = st.number_input("Dış Genişlik W (mm)", min_value=0.01, value=parsed_data["w"] if parsed_data["w"] > 0 else 50.0)
            p_h = st.number_input("Dış Yükseklik H (mm)", min_value=0.01, value=parsed_data["h"] if parsed_data["h"] > 0 else 30.0)
            gramaj_kg_m = st.number_input("Ağırlık (gr/mt)", min_value=0.01, value=parsed_data["gramaj"] if parsed_data["gramaj"] > 0 else 1250.0) / 1000 
            renk = "purple"
        elif profil_tipi == "Kutu Profil":
            p_w = st.number_input("Genişlik W (mm)", min_value=0.01, value=50.0)
            p_h = st.number_input("Yükseklik H (mm)", min_value=0.01, value=30.0)
            t = st.number_input("Et Kalınlığı t (mm)", min_value=0.01, value=1.5)
            t_eff = min(t, p_w/2, p_h/2)
            gramaj_kg_m = ((p_w * p_h) - ((p_w - 2*t_eff) * (p_h - 2*t_eff))) * 0.00271
            renk = "royalblue"
        elif profil_tipi == "Boru":
            p_w = st.number_input("Dış Çap Ø (mm)", min_value=0.01, value=40.0)
            p_h = p_w 
            t = st.number_input("Et Kalınlığı t (mm)", min_value=0.01, value=2.0)
            t_eff = min(t, p_w/2)
            gramaj_kg_m = ((math.pi * (p_w/2)**2) - (math.pi * ((p_w/2) - t_eff)**2)) * 0.00271
            renk = "silver"
        elif profil_tipi == "L Profil":
            p_w = st.number_input("Genişlik W (mm)", min_value=0.01, value=40.0)
            p_h = st.number_input("Yükseklik H (mm)", min_value=0.01, value=40.0)
            t = st.number_input("Et Kalınlığı t (mm)", min_value=0.01, value=3.0)
            t_eff = min(t, p_w, p_h)
            gramaj_kg_m = ((p_w * t_eff) + ((p_h - t_eff) * t_eff)) * 0.00271
            renk = "forestgreen"
        elif profil_tipi == "Dolu Mil":
            p_w = st.number_input("Çap Ø (mm)", min_value=0.01, value=20.0)
            p_h = p_w
            gramaj_kg_m = (math.pi * (p_w/2)**2) * 0.00271
            renk = "darkgray"

        st.info(f"⚖️ **Birim Ağırlık:** {gramaj_kg_m:.3f} kg/mt")
        kesim_boyu = st.number_input("Kesim Boyu (mm)", min_value=0.01, value=6000.0)

    with col_pal:
        st.subheader("2. Palet Sınırları")
        palet_w = st.number_input("Palet Genişliği (mm)", min_value=0.01, value=1000.0)
        palet_l_value = 1200.0 if "Dikey" in yon else float(max(0.01, kesim_boyu))
        palet_l = st.number_input("Palet Uzunluğu (mm)", min_value=0.01, value=palet_l_value)
        palet_max_h = st.number_input("Müşteri Max İstif (mm)", min_value=0.01, value=1200.0)
        alt_ahsap = st.number_input("Ahşap Kalınlığı (mm)", min_value=0.0, value=140.0)
        ara_katman = st.checkbox("Bağlar/Katlar Arası Karton", value=True)
        katman_t = 2.0 if ara_katman else 0.0

    with col_pack:
        st.subheader("3. Akıllı Paket Düzeni")
        palet_h_net = palet_max_h - alt_ahsap
        
        # Oryantasyona Göre Limit Belirleme
        if "Yatay" in yon:
            opt_limit_x, opt_limit_y = palet_w, palet_h_net
        else: # Dikey
            opt_limit_x, opt_limit_y = palet_w, palet_l
            
        opt_c, opt_r = optimize_bundle(p_w, p_h, profil_tipi, opt_limit_x, opt_limit_y)
        
        if profil_tipi == "L Profil": opt_c = max(1, opt_c // 2) * 2 
        
        b1, b2 = st.columns(2)
        bag_yan_yana = b1.number_input("Yan Yana Sıra (X Ekseni)", min_value=1, value=int(opt_c))
        bag_ust_uste = b2.number_input("Derinlik/Üst Üste Sıra", min_value=1, value=int(opt_r))
        
        if profil_tipi == "L Profil":
            calc_min_w = (bag_yan_yana / 2.0) * p_w
            calc_min_h = bag_ust_uste * p_h
            bag_ici_adet = bag_yan_yana * bag_ust_uste
        elif profil_tipi in ["Boru", "Dolu Mil"]:
            calc_min_w = bag_yan_yana * p_w
            calc_min_h = p_w + (bag_ust_uste - 1) * (p_w * 0.866)
            bag_ici_adet = bag_yan_yana * bag_ust_uste - (bag_ust_uste // 2)
        else:
            calc_min_w = bag_yan_yana * p_w
            calc_min_h = bag_ust_uste * p_h
            bag_ici_adet = bag_yan_yana * bag_ust_uste

        st.caption("Ambalaj payı için ebatları manuel büyütebilirsiniz.")
        bag_w = st.number_input("Paket Dış Genişliği (mm)", min_value=float(calc_min_w), value=float(calc_min_w))
        h_label = "Paket Dış Yüksekliği (mm)" if "Yatay" in yon else "Paket Dış Derinliği (mm)"
        bag_h = st.number_input(h_label, min_value=float(calc_min_h), value=float(calc_min_h))

        # ORYANTASYONA GÖRE FİZİKSEL HESAPLAMA
        if "Yatay" in yon:
            box_w, box_d, box_h = bag_w, kesim_boyu, bag_h
        else:
            box_w, box_d, box_h = bag_w, bag_h, kesim_boyu

        fit_x = max(1, int(palet_w // box_w))
        fit_y = max(1, int(palet_l // box_d))
        fit_z = max(1, int(palet_h_net // (box_h + katman_t)))
        
        palet_ici_profil = fit_x * fit_y * fit_z * bag_ici_adet
        palet_agirlik = (palet_ici_profil * (kesim_boyu/1000) * gramaj_kg_m) + 25.0 
        otomatik_palet = math.ceil(toplam_siparis_adedi / max(1, palet_ici_profil))
        
        st.success(f"📦 Palette: **{palet_ici_profil} Adet** | ⚖️ Palet Brüt: **{palet_agirlik:.1f} kg**")
        uretilecek_palet = st.number_input("Üretilecek Palet Sayısı", min_value=1, value=otomatik_palet)

        if st.button("🛒 Sevkiyat Planına Ekle", type="primary", use_container_width=True):
            st.session_state.cart.append({
                "siparis": siparis_no, "alasim": alasim, "tip": profil_tipi, 
                "palet_adet": uretilecek_palet, "adet_profil": palet_ici_profil * uretilecek_palet,
                "p_w": palet_w, "p_l": palet_l, "p_h": alt_ahsap + (fit_z * (box_h + katman_t)),
                "agirlik": palet_agirlik, "renk": renk
            })
            st.rerun()

    # --- 3D GÖRSELLER ---
    st.divider()
    t1, t2, t3 = st.tabs(["📏 Kesit (2D)", "📦 Bağ Görseli (3D)", "🏗️ Palet İstifleme Görseli (3D)"])
    
    with t1:
        st.write("**Profil Geometrisi Temsili**")
        fig2d = go.Figure()
        if profil_tipi in ["Boru", "Dolu Mil"]:
            fig2d.add_shape(type="circle", x0=0, y0=0, x1=p_w, y1=p_h, line=dict(color=renk, width=4), fillcolor="lightgray")
        elif profil_tipi == "L Profil":
            fig2d.add_trace(go.Scatter(x=[0, p_w, p_w, t_eff, t_eff, 0, 0], y=[0, 0, t_eff, t_eff, p_h, p_h, 0], fill="toself", fillcolor=renk, line_color="black"))
        else:
            fig2d.add_shape(type="rect", x0=0, y0=0, x1=p_w, y1=p_h, line=dict(color="black", width=2), fillcolor=renk)
        fig2d.update_layout(xaxis=dict(scaleanchor="y", scaleratio=1), width=400, height=400, showlegend=False)
        st.plotly_chart(fig2d)
        
    with t2:
        st.write(f"**Profil Dizilimi** (Paket Sınırı: {box_w}x{box_d}x{box_h} mm)")
        fig_pkg = go.Figure()
        fig_pkg.add_trace(create_3d_box(0, 0, 0, box_w, box_d, box_h, 'rgba(255,255,255,0.1)', 'Bağ Sınırı'))
        
        x_gap = (bag_w - calc_min_w) / 2
        y_gap = (bag_h - calc_min_h) / 2 if "Dikey" in yon else 0
        z_gap = (bag_h - calc_min_h) / 2 if "Yatay" in yon else 0

        if profil_tipi == "L Profil":
            for i in range(int(bag_yan_yana/2)):
                for j in range(int(bag_ust_uste)):
                    if "Yatay" in yon:
                        x_pos, z_pos = x_gap + (i * p_w), z_gap + (j * p_h)
                        fig_pkg.add_trace(create_3d_box(x_pos, 0, z_pos, p_w, kesim_boyu, p_h/2.2, renk, 'L'))
                        fig_pkg.add_trace(create_3d_box(x_pos, 0, z_pos+(p_h/2.2), p_w, kesim_boyu, p_h/2.2, 'darkgreen', 'L'))
                    else:
                        x_pos, y_pos = x_gap + (i * p_w), y_gap + (j * p_h)
                        fig_pkg.add_trace(create_3d_box(x_pos, y_pos, 0, p_w, p_h/2.2, kesim_boyu, renk, 'L'))
                        fig_pkg.add_trace(create_3d_box(x_pos, y_pos+(p_h/2.2), 0, p_w, p_h/2.2, kesim_boyu, 'darkgreen', 'L'))
        elif profil_tipi in ["Boru", "Dolu Mil"]:
            r = p_w / 2
            for j in range(int(bag_ust_uste)):
                offset = r if j % 2 != 0 else 0
                for i in range(int(bag_yan_yana) if j % 2 == 0 else int(bag_yan_yana)-1):
                    if "Yatay" in yon:
                        xc, zc = x_gap + offset + (i * p_w) + r, z_gap + (j * (p_w * 0.866)) + r
                        fig_pkg.add_trace(create_3d_cylinder(xc, 0, zc, r*0.95, kesim_boyu, renk, 'Y', yon="Yatay"))
                    else:
                        xc, yc = x_gap + offset + (i * p_w) + r, y_gap + (j * (p_w * 0.866)) + r
                        fig_pkg.add_trace(create_3d_cylinder(xc, yc, 0, r*0.95, kesim_boyu, renk, 'D', yon="Dikey"))
        else: 
            for i in range(int(bag_yan_yana)):
                for j in range(int(bag_ust_uste)):
                    if "Yatay" in yon:
                        fig_pkg.add_trace(create_3d_box(x_gap + i*p_w, 0, z_gap + j*p_h, p_w*0.95, kesim_boyu, p_h*0.95, renk, 'K'))
                    else:
                        fig_pkg.add_trace(create_3d_box(x_gap + i*p_w, y_gap + j*p_h, 0, p_w*0.95, p_h*0.95, kesim_boyu, renk, 'K'))
        
        fig_pkg.update_layout(scene=dict(aspectmode='data', **cam_angle), height=600, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig_pkg, use_container_width=True)

    with t3:
        st.write(f"**Palet Üzerine İstifleme** ({fit_x} Yan x {fit_y} Derinlik x {fit_z} Kat)")
        fig_pal = go.Figure()
        fig_pal.add_trace(create_3d_box(0, 0, 0, palet_w, palet_l, alt_ahsap, 'saddlebrown', 'Ahşap Palet'))
        
        for k in range(fit_z):
            z_base = alt_ahsap + (k * (box_h + katman_t))
            if ara_katman and k > 0:
                fig_pal.add_trace(create_3d_box(0, 0, z_base - katman_t, palet_w, palet_l, katman_t, 'peru', 'Katman'))
            for y in range(fit_y):
                for x in range(fit_x):
                    fig_pal.add_trace(create_3d_box(x*box_w, y*box_d, z_base, box_w-2, box_d-2, box_h-2, renk, 'Bağ', 0.8))
        
        fig_pal.add_trace(create_3d_box(-5, -5, alt_ahsap, palet_w+10, palet_l+10, (fit_z*(box_h+katman_t)), 'rgba(200,220,255,0.2)', 'Shrink'))
        fig_pal.update_layout(scene=dict(aspectmode='data', **cam_angle), height=700, margin=dict(l=0,r=0,b=0,t=0))
        st.plotly_chart(fig_pal, use_container_width=True)

# --- MODÜL 2: TIR & SEVKİYAT SİMÜLASYONU ---
elif menu == "🚛 Tır & Sevkiyat Dizilimi":
    st.header("Sevkiyat Yönetimi ve Yükleme Planı")
    if not st.session_state.cart:
        st.warning("Sevkiyat listesi boş. 'Üretim' sekmesinden sipariş ekleyin.")
    else:
        edited_df = st.data_editor(pd.DataFrame(st.session_state.cart), num_rows="dynamic", use_container_width=True, key="cart_editor")
        st.session_state.cart = edited_df.to_dict('records')
        
        col_truck, col_list = st.columns([2, 1])
        with col_truck:
            t_w, t_l, t_h = 2450.0, 13600.0, 2600.0
            fig_truck = go.Figure()
            fig_truck.add_trace(create_3d_box(0, 0, 0, t_w, t_l, t_h, 'rgba(150,150,150,0.1)', 'Dorse'))
            
            cur_x, cur_y, row_max_l = 0.0, 0.0, 0.0
            for idx, row in edited_df.iterrows():
                kalan_palet = int(row['palet_adet'])
                p_w, p_l, p_h = float(row['p_w']), float(row['p_l']), float(row['p_h'])
                if p_h > t_h or p_w > t_w or p_l > t_l: continue 
                
                while kalan_palet > 0:
                    if cur_x + p_w > t_w:
                        cur_x, cur_y = 0, cur_y + row_max_l + 20 
                        row_max_l = 0
                    if cur_y + p_l > t_l: break 
                    
                    if kalan_palet >= 2 and (p_h * 2) <= t_h:
                        fig_truck.add_trace(create_3d_box(cur_x, cur_y, 0, p_w, p_l, p_h, row['renk'], f"Alt", 1.0))
                        fig_truck.add_trace(create_3d_box(cur_x, cur_y, p_h, p_w, p_l, p_h, row['renk'], f"Üst", 0.8))
                        kalan_palet -= 2
                    else:
                        fig_truck.add_trace(create_3d_box(cur_x, cur_y, 0, p_w, p_l, p_h, row['renk'], row['siparis'], 1.0))
                        kalan_palet -= 1
                    
                    row_max_l = max(row_max_l, p_l)
                    cur_x += p_w
                        
            fig_truck.update_layout(scene=dict(aspectmode='data', **cam_angle), height=700, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_truck, use_container_width=True)

        with col_list:
            ceki_df = edited_df[['siparis', 'alasim', 'tip', 'palet_adet', 'adet_profil', 'agirlik']].copy()
            st.dataframe(ceki_df, use_container_width=True)
            if st.button("🗑️ Tüm Sevkiyatı Sıfırla", type="primary"):
                st.session_state.cart = []; st.rerun()