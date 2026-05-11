# --- MODÜL 2: TIR & SEVKİYAT SİMÜLASYONU ---
elif menu == "🚛 Tır & Sevkiyat Dizilimi":
    st.header("Sevkiyat Yönetimi ve Yükleme Planı")
    if not st.session_state.cart:
        st.warning("Sevkiyat listesi şu an boş. Lütfen sol menüden 'Üretim & Paketleme' sekmesine dönüp sipariş ekleyin.")
    else:
        st.info("ℹ️ Aşağıdaki tablo etkileşimlidir. Palet adetlerini doğrudan hücrenin içine tıklayarak değiştirebilirsiniz. Değişiklikler anında 3D Tır simülasyonuna yansıyacaktır.")
        edited_df = st.data_editor(pd.DataFrame(st.session_state.cart), num_rows="dynamic", use_container_width=True, key="cart_editor")
        
        yeni_liste = edited_df.to_dict('records')
        if str(yeni_liste) != str(st.session_state.cart):
            st.session_state.cart = yeni_liste
            st.rerun()
            
        col_truck, col_list = st.columns([2, 1])
        with col_truck:
            st.write("🚚 **3D Dorse Yükleme Simülasyonu** (Dorse Max Kapasite: Uzunluk 13.6m x Genişlik 2.45m x Tavan 2.6m)")
            t_w, t_l, t_h = 2450.0, 13600.0, 2600.0
            fig_truck = go.Figure()
            fig_truck.add_trace(create_3d_box(0, 0, 0, t_w, t_l, t_h, 'rgba(150,150,150,0.1)', 'Dorse Sınırı'))
            
            cur_x, cur_y, row_max_l = 0.0, 0.0, 0.0
            truck_color_groups = {} 
            
            for idx, row in edited_df.iterrows():
                kalan_palet = int(row['palet_adet'])
                p_w, p_l, p_h = float(row['p_w']), float(row['p_l']), float(row['p_h'])
                renk = row['renk']
                if renk not in truck_color_groups: truck_color_groups[renk] = []
                
                # Tıra sığmayan devasa paletleri yoksay
                if p_h > t_h or p_w > t_w or p_l > t_l: 
                    st.error(f"Hata: {row['siparis']} numaralı siparişteki palet tıra sığmayacak kadar büyük!")
                    continue 
                
                while kalan_palet > 0:
                    if cur_x + p_w > t_w:
                        cur_x, cur_y = 0, cur_y + row_max_l + 20 
                        row_max_l = 0
                    if cur_y + p_l > t_l: 
                        st.warning("⚠️ Tır dorse uzunluğu (13.6m) doldu! Kalan paletler dışarıda kaldı.")
                        break 
                    
                    # --- YENİ DİNAMİK İSTİF MANTIĞI ---
                    # 1. Z eksenine (üst üste) fiziksel olarak kaç palet sığar?
                    max_z_stack = max(1, int(t_h // p_h)) 
                    
                    # 2. Elimizde kalan palet sayısını aşmayacak şekilde yığın yap.
                    stack_count = min(kalan_palet, max_z_stack) 
                    
                    # 3. Yığını dorseye yerleştir
                    for z_i in range(stack_count):
                        z_pos = z_i * p_h
                        truck_color_groups[renk].append((cur_x, cur_y, z_pos, p_w, p_l, p_h))
                    
                    # 4. Yüklenenleri kalanlardan düş ve x ekseninde (yan tarafa) ilerle
                    kalan_palet -= stack_count
                    row_max_l = max(row_max_l, p_l)
                    cur_x += p_w
            
            for c, boxes in truck_color_groups.items():
                trace = create_batch_boxes(boxes, c, "Palet", 0.9)
                if trace: fig_truck.add_trace(trace)
                        
            fig_truck.update_layout(scene=dict(aspectmode='data', **cam_angle), height=700, margin=dict(l=0,r=0,b=0,t=0))
            st.plotly_chart(fig_truck, use_container_width=True)

        with col_list:
            st.subheader("📄 Çeki Listesi (Packing List)")
            ceki_df = edited_df[['siparis', 'alasim', 'tip', 'palet_adet', 'adet_profil', 'agirlik']].copy()
            st.dataframe(ceki_df, use_container_width=True)
            if st.button("🗑️ Tüm Sevkiyatı Sıfırla", type="primary", help="Tablodaki tüm yüklemeleri siler ve dorseyi boşaltır."):
                st.session_state.cart = []; st.rerun()