import os
import random
import time
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import httpx
from aging_engine import parse_excel, compute_aging

RESEND_API_KEY = os.environ.get('RESEND_API_KEY', '')
OTP_VALIDITY_SECONDS = 600  # 10 minutes


def send_otp(email: str, otp: str) -> bool:
    """Envoie l'OTP par email via Resend. Retourne True si succes."""
    if not RESEND_API_KEY:
        return False
    try:
        resp = httpx.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {RESEND_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'from': 'Agent Créances <noreply@courticonnect.ca>',
                'to': [email],
                'subject': "🔐 Votre code d'accès — Agent Créances",
                'html': f"""
<div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto;padding:32px;">
  <h2 style="color:#1e40af;">Agent Créances — Code d'accès</h2>
  <p>Votre code d'accès à usage unique :</p>
  <div style="font-size:36px;font-weight:bold;letter-spacing:8px;
              color:#C9A84C;background:#f8fafc;
              padding:20px;text-align:center;border-radius:8px;
              margin:24px 0;">
    {otp}
  </div>
  <p style="color:#6b7280;font-size:13px;">
    Ce code est valide 10 minutes.<br>
    Si vous n'avez pas demandé cet accès, ignorez cet email.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0;">
  <p style="color:#6b7280;font-size:12px;">
    Agent Créances — VibeCoding IA · Analyse due diligence créances
  </p>
</div>
                """,
            },
            timeout=10,
        )
        return resp.status_code in (200, 201)
    except Exception:
        return False


def check_password():
    if st.session_state.get('authenticated'):
        return True

    st.markdown(
        "<h2 style='color:#1e40af;'>🔐 Agent Créances — Accès sécurisé</h2>",
        unsafe_allow_html=True,
    )
    st.markdown("Entrez votre adresse email pour recevoir un code d'accès.")

    # STEP 1 - Saisie email
    if not st.session_state.get('otp_sent'):
        email = st.text_input("Adresse email professionnelle", placeholder="nom@entreprise.com")
        if st.button("Recevoir mon code →", type="primary"):
            if not email or '@' not in email:
                st.error("Adresse email invalide.")
                return False
            otp = str(random.randint(100000, 999999))
            st.session_state['otp_code']  = otp
            st.session_state['otp_email'] = email
            st.session_state['otp_time']  = time.time()
            if send_otp(email, otp):
                st.session_state['otp_sent'] = True
                st.rerun()
            else:
                st.error("Erreur d'envoi email. Vérifiez la configuration RESEND_API_KEY.")
        return False

    # STEP 2 - Saisie OTP
    st.success(
        f"✅ Code envoyé à **{st.session_state['otp_email']}** "
        "— vérifiez vos spams si besoin."
    )
    otp_input = st.text_input("Code à 6 chiffres", max_chars=6, placeholder="123456")

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("Valider", type="primary"):
            elapsed = time.time() - st.session_state.get('otp_time', 0)
            if elapsed > OTP_VALIDITY_SECONDS:
                st.error("Code expiré. Recommencez.")
                for k in ['otp_sent', 'otp_code', 'otp_time']:
                    st.session_state.pop(k, None)
            elif otp_input == st.session_state.get('otp_code'):
                st.session_state['authenticated'] = True
                st.session_state['user_email']    = st.session_state['otp_email']
                st.rerun()
            else:
                st.error("Code incorrect.")
    with col2:
        if st.button("Changer d'email"):
            for k in ['otp_sent', 'otp_code', 'otp_time', 'otp_email']:
                st.session_state.pop(k, None)
            st.rerun()

    return False


def fmt_mad(val):
    return f"{val:,.0f} MAD".replace(",", " ")


def main():
    st.set_page_config(
        page_title="Agent Creances",
        page_icon="📊",
        layout="wide",
    )

    if not check_password():
        return

    st.markdown(
        "<h1 style='color:#1e40af;'>📊 Agent Créances — Analyse Due Diligence</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#6b7280;'>Uploadez votre balance âgée Excel — résultats "
        "instantanés, aucune donnée stockée.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    uploaded = st.file_uploader(
        "📁 Déposez votre fichier Balance Âgée (.xlsx)",
        type=["xlsx"],
        help="Formats supportés : BEST MILK (12 colonnes) ou SWF / FANDY SOUSS (8 colonnes)",
    )

    if uploaded is None:
        st.info("👆 Uploadez un fichier Excel pour démarrer l'analyse.")
        return

    with st.spinner("Analyse en cours..."):
        try:
            file_bytes = uploaded.read()
            df, meta = parse_excel(file_bytes)
            kpis = compute_aging(df)
        except ValueError as e:
            err = str(e)
            if err == 'FORMAT_C_DETECTED':
                st.warning("⚠️ Balance auxiliaire détectée — ce n'est pas une balance âgée")
                st.markdown("""
Ce fichier contient des **mouvements comptables** (Débit / Crédit / SFD / SFC)
mais **pas de répartition par ancienneté**.

L'Agent Créances nécessite une **Balance Âgée** avec les tranches :
> 0-30 jours · 30-60 jours · 60-90 jours · Plus de 90 jours

---
### 📂 Comment exporter une Balance Âgée depuis votre logiciel

| Logiciel | Chemin d'accès |
|----------|---------------|
| **Sage 100** | `États > Clients > Balance âgée` |
| **Sage FRP 1000** | `Comptabilité > Clients > Analyse de l'encours > Balance âgée` |
| **Cegid** | `Comptabilité > Clients > États > Balance âgée` |
| **SAP B1** | `Comptabilité > Rapports financiers > Financier > Balance âgée` |
| **SAP FI (ECC/S4)** | `Transaction FBL5N > sélectionner postes ouverts > exporter Excel` |
| **Oracle EBS** | `Receivables > Reports > Aging > Aging – 7 Buckets Report` |
| **Oracle Fusion** | `Receivables > Reports and Analytics > Aging by Account Detail` |
| **JD Edwards** | `Menu G03B > Report > Customer Aging Report (R03B4201A)` |
| **Microsoft Dynamics 365** | `Crédit et relances > Collections > Soldes chronologiques > Exporter` |
| **Microsoft Dynamics NAV/BC** | `Comptabilité > Clients > Balance âgée clients` |
| **Odoo** | `Comptabilité > Clients > Balance âgée` |
| **CIEL** | `Éditions > Balances > Balance âgée clients` |
| **EBP** | `Comptabilité > États > Balance âgée clients` |
| **QuickBooks** | `Rapports > Clients > Balance âgée des clients` |

---
💡 **Conseil** : au moment de l'export, choisissez le format **Excel (.xlsx)**
et sélectionnez les tranches **30 / 60 / 90 jours** ou **30 / 60 / 90 / 120 jours**.
                """)
            elif err == 'FORMAT_UNKNOWN':
                st.error("❌ Format non reconnu. Uploadez une Balance Âgée clients au format Excel (.xlsx).")
                st.caption("Formats supportés : BEST MILK (12 colonnes), SWF/FANDY SOUSS (8 colonnes).")
            else:
                st.error(f"❌ Erreur : {e}")
            return
        except Exception as e:
            st.error(f"❌ Erreur inattendue : {e}")
            return

    fmt_label = (
        "BEST MILK (12 colonnes)" if meta['format'] == 'FORMAT_A'
        else "SWF / FANDY SOUSS (8 colonnes)"
    )
    st.success(
        f"✅ Fichier analysé — Format détecté : **{fmt_label}** · "
        f"Onglet : `{meta['sheet_name']}` · "
        f"**{meta['nb_clients']} clients** ({meta['nb_skipped']} lignes ignorées)"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Total créances", fmt_mad(kpis['total']))
    c2.metric("🔴 > 120 jours", fmt_mad(kpis['buckets']['> 120 j']))
    c3.metric("⚠️ Clients critiques", f"{kpis['nb_critiques']}")
    c4.metric("📈 % critique", f"{kpis['pct_critique']:.1f}%")

    st.divider()

    col_left, col_right = st.columns([1.2, 1])

    colors = ['#4ade80', '#3b82f6', '#f59e0b', '#f97316', '#ef4444', '#7f1d1d']

    with col_left:
        st.markdown("#### Répartition par ancienneté")
        labels = list(kpis['buckets'].keys())
        values = list(kpis['buckets'].values())
        fig = go.Figure(go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[fmt_mad(v) for v in values],
            textposition='outside',
        ))
        fig.update_layout(
            height=350,
            margin=dict(t=20, b=20),
            yaxis_title="MAD",
            plot_bgcolor='white',
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### Répartition (camembert)")
        non_zero = {k: v for k, v in kpis['buckets'].items() if v > 0}
        if non_zero:
            fig2 = go.Figure(go.Pie(
                labels=list(non_zero.keys()),
                values=list(non_zero.values()),
                hole=0.4,
                marker_colors=colors[:len(non_zero)],
            ))
            fig2.update_layout(height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Aucune créance à afficher.")

    st.divider()

    st.markdown("#### 🚨 Top 10 clients prioritaires (> 120 jours)")
    if len(kpis['top10']) > 0:
        st.dataframe(
            kpis['top10'].style.format({
                '>120j (MAD)':    '{:,.0f}',
                'Total du (MAD)': '{:,.0f}',
            }),
            use_container_width=True,
            height=380,
        )
    else:
        st.info("Aucun client avec créances > 120 jours.")

    st.divider()

    st.markdown("#### 📥 Exporter les résultats")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="⬇️ Télécharger CSV complet",
        data=csv,
        file_name=f"aging_{uploaded.name.replace('.xlsx', '')}.csv",
        mime="text/csv",
    )

    st.caption(
        "🔒 Aucune donnée n'est stockée — traitement 100% en mémoire. "
        "Fermez l'onglet pour effacer les résultats."
    )


if __name__ == "__main__":
    main()
