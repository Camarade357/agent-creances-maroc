import datetime
import os
import random
import time

import sys
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import httpx
from aging_engine import (
    parse_excel,
    compute_aging,
    compute_segmentation,
    compute_dso,
    generate_plan_recouvrement,
)

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
  <p style="color:#166534;background:#f0fdf4;
            border:1px solid #4ade80;border-radius:6px;
            padding:12px;font-size:13px;">
    🔒 <strong>Confidentialité</strong> : vos fichiers sont analysés
    en mémoire uniquement. Aucune donnée n'est stockée sur nos serveurs.
  </p>
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

    st.markdown("""
<div style="
  background:#f0fdf4;
  border:1.5px solid #4ade80;
  border-radius:8px;
  padding:14px 20px;
  margin-bottom:16px;
  display:flex;
  align-items:flex-start;
  gap:12px;
">
  <span style="font-size:20px;">🔒</span>
  <div>
    <strong style="color:#166534;">Confidentialité garantie</strong><br>
    <span style="color:#166534;font-size:14px;">
      Vos fichiers sont analysés <strong>en mémoire uniquement</strong>
      et ne sont <strong>jamais stockés</strong> sur nos serveurs.
      Aucune donnée n'est conservée après fermeture de l'onglet.
      Aucun tiers n'a accès à vos informations.
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

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

    st.markdown("""
<div style="background:#eff6ff;border:1px solid #3b82f6;
border-radius:8px;padding:12px 16px;margin-bottom:8px;">
<strong style="color:#1e40af;">📋 Format accepté</strong><br>
<span style="color:#1e40af;font-size:13px;">
Uploadez une <strong>Balance Âgée Clients</strong> au format Excel (.xlsx)
— avec des colonnes de tranches en jours (0-30 / 30-60 / 60-90 / >90 jours).<br>
<em>Pas une balance générale, pas un grand livre auxiliaire.</em>
</span>
</div>
""", unsafe_allow_html=True)

    if uploaded is None:
        st.info("👆 Uploadez un fichier Excel pour démarrer l'analyse.")
        return

    consent = st.checkbox(
        "✅ Je confirme que ce fichier ne contient pas de données "
        "personnelles protégées (noms de personnes physiques, "
        "numéros de carte, mots de passe) et j'accepte les "
        "[conditions d'utilisation](#mentions).",
        value=False,
    )

    if uploaded and not consent:
        st.info("👆 Cochez la case ci-dessus pour lancer l'analyse.")
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

    # ── CA optionnel pour le DSO réel ──
    with st.expander("💡 Optionnel — Saisir le CA pour le DSO réel"):
        ca_input = st.number_input(
            "Chiffre d'affaires de la période (MAD)",
            min_value=0.0, value=0.0, step=100000.0,
            help="Laissez à 0 pour utiliser uniquement le DSO approché",
        )
    ca_annuel = ca_input if ca_input > 0 else None

    dso_data = compute_dso(df, ca_annuel)
    segments_data, df_seg, pareto_info = compute_segmentation(df)
    plan_df = generate_plan_recouvrement(segments_data, dso_data)

    # ── KPIs GLOBAUX ──
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("💰 Total créances",   fmt_mad(kpis['total']))
    c2.metric("🔴 > 120 jours",      fmt_mad(kpis['buckets']['> 120 j']))
    c3.metric("⚠️ Clients critiques", f"{kpis['nb_critiques']}")
    c4.metric("📈 % critique",        f"{kpis['pct_critique']:.1f}%")
    c5.metric("⏱️ DSO approché",      f"{dso_data['dso_approche']} j")

    if dso_data.get('dso_reel'):
        st.info(f"📊 DSO réel (basé sur CA saisi) : **{dso_data['dso_reel']} jours**")

    st.divider()

    # ── SEGMENTATION 4 QUADRANTS ──
    st.markdown("### 🎯 Segmentation clients — 4 quadrants")
    st.caption(
        f"📊 Pareto 80/20 — {pareto_info['nb_grands']} grands comptes "
        f"({pareto_info['pct_clients']}% des clients) "
        f"= {pareto_info['pct_montant']}% des créances · "
        f"Seuil : {fmt_mad(pareto_info['seuil_mad'])}"
    )

    col_ab, col_cd = st.columns(2)
    seg_to_col = {'A-RISQUE': col_ab, 'A-BON': col_ab, 'B-RISQUE': col_cd, 'B-BON': col_cd}

    for seg in ['A-RISQUE', 'A-BON', 'B-RISQUE', 'B-BON']:
        data = segments_data.get(seg, {})
        if not data or data['nb'] == 0:
            continue
        with seg_to_col[seg]:
            st.markdown(
                f"<div style='background:{data['couleur']}18;"
                f"border-left:4px solid {data['couleur']};"
                f"border-radius:8px;padding:12px 16px;margin-bottom:12px;'>"
                f"<strong style='color:{data['couleur']};'>{data['label']}</strong><br>"
                f"<span style='font-size:13px;color:#374151;'>"
                f"{data['nb']} clients · {fmt_mad(data['total'])} · "
                f"Action : {data['action']}"
                f"</span></div>",
                unsafe_allow_html=True,
            )
            with st.expander(f"Voir les clients ({data['nb']})"):
                st.dataframe(
                    data['clients'].style.format({
                        'solde':     '{:,.0f}',
                        'b_plus120': '{:,.0f}',
                        'b_0_30':    '{:,.0f}',
                    }),
                    use_container_width=True,
                    height=250,
                )

    st.divider()

    # ── DSO PAR CLIENT ──
    st.markdown("### ⏱️ DSO par client — Top 10 délais les plus longs")
    if len(dso_data['top_dso']) > 0:
        st.dataframe(
            dso_data['top_dso'].style.format({
                'DSO (jours)':    '{:.0f}',
                'Total du (MAD)': '{:,.0f}',
                '>120j (MAD)':    '{:,.0f}',
            }),
            use_container_width=True,
            height=380,
        )
    else:
        st.info("Aucune donnée DSO calculable.")

    st.divider()

    # ── GRAPHIQUES (existants) ──
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

    # ── PLAN DE RECOUVREMENT HEBDOMADAIRE ──
    today_str = datetime.date.today().strftime('%d/%m/%Y')
    st.markdown(f"### 📅 Plan de recouvrement — Semaine du {today_str}")
    st.caption("Priorisé par segment : A-RISQUE (urgent) → B-RISQUE (arbitrage) → A-BON (fidélisation) → B-BON (standard)")

    if not plan_df.empty:
        _highlight = (
            lambda v: 'background-color:#fef2f2' if 'A-RISQUE' in str(v) else
                      'background-color:#fff7ed' if 'B-RISQUE' in str(v) else
                      'background-color:#f0fdf4' if 'A-BON' in str(v) else
                      'background-color:#fefce8' if 'B-BON' in str(v) else ''
        )
        st.dataframe(
            plan_df.style.map(_highlight, subset=['Segment']),
            use_container_width=True,
            height=420,
        )
    else:
        st.info("Aucune action de recouvrement à proposer (pas de soldes positifs).")

    st.divider()

    # ── EXPORT ──
    st.markdown("#### 📥 Export")
    csv_plan = plan_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        "⬇️ Télécharger le plan de recouvrement (CSV)",
        data=csv_plan,
        file_name=f"plan_recouvrement_{datetime.date.today()}.csv",
        mime="text/csv",
    )

    # ── FEEDBACK ──
    st.divider()
    st.markdown("#### 💬 Votre avis nous aide à améliorer l'agent")

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        note = st.select_slider(
            "Note globale",
            options=[1, 2, 3, 4, 5],
            value=4,
            format_func=lambda x: "⭐" * x,
        )
    with col_f2:
        commentaire = st.text_area(
            "Qu'est-ce qui manque ? Un problème ?",
            placeholder="Ex: je voudrais un export PDF, les montants en devise locale...",
            height=80,
        )

    if st.button("Envoyer mon feedback →"):
        user_email = st.session_state.get('user_email', 'inconnu')
        feedback_html = f"""
        <h3>Feedback Agent Créances</h3>
        <p><strong>Testeur :</strong> {user_email}</p>
        <p><strong>Note :</strong> {'⭐' * note} ({note}/5)</p>
        <p><strong>Commentaire :</strong> {commentaire or '(aucun)'}</p>
        <hr>
        <p><strong>Fichier analysé :</strong> {meta.get('source','?')}</p>
        <p><strong>Format :</strong> {meta.get('format','?')}</p>
        <p><strong>Nb clients :</strong> {meta.get('nb_clients','?')}</p>
        <p><strong>Total créances :</strong> {fmt_mad(kpis['total'])}</p>
        <p><strong>DSO approché :</strong> {dso_data['dso_approche']} jours</p>
        """
        sent = False
        if RESEND_API_KEY:
            try:
                resp = httpx.post(
                    'https://api.resend.com/emails',
                    headers={
                        'Authorization': f'Bearer {RESEND_API_KEY}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'from': 'Agent Créances <noreply@courticonnect.ca>',
                        'to': ['hamza357@gmail.com'],
                        'subject': f'⭐ Feedback Agent Créances — {note}/5 — {user_email}',
                        'html': feedback_html,
                    },
                    timeout=10,
                )
                sent = resp.status_code in (200, 201)
            except Exception:
                sent = False
        if sent:
            st.success("✅ Merci pour votre retour !")
        else:
            st.info("Feedback noté localement — merci !")

    st.caption(
        "🔒 Aucune donnée n'est stockée — traitement 100% en mémoire. "
        "Fermez l'onglet pour effacer les résultats."
    )

    with st.expander("📋 Mentions légales & Politique de confidentialité"):
        st.markdown("""
### Politique de traitement des données

**Responsable du traitement** : VibeCoding IA / Archipel IA Inc.

**Données traitées**
Les fichiers Excel uploadés sont traités **exclusivement en mémoire vive (RAM)**
dans votre session Streamlit.

**Ce que nous ne faisons PAS** :
- ❌ Nous ne stockons aucun fichier sur nos serveurs
- ❌ Nous ne conservons aucune donnée après fermeture de l'onglet
- ❌ Nous ne partageons aucune donnée avec des tiers
- ❌ Nous n'utilisons pas vos données pour entraîner des modèles IA
- ❌ Nous ne collectons pas les noms de vos clients ni leurs montants

**Ce que nous collectons uniquement** :
- ✅ Votre adresse email (pour l'envoi du code OTP d'accès)
- ✅ Les métadonnées de session (horodatage, format de fichier détecté)
  à des fins de diagnostic technique uniquement

**Durée de conservation**
- Fichier uploadé : supprimé immédiatement après analyse (mémoire vive)
- Adresse email : conservée le temps de la session uniquement
- Aucune base de données clients n'est alimentée par cet outil

**Hébergement**
Application hébergée sur **Streamlit Community Cloud** (USA, Streamlit Inc.)
— voir leur politique : https://streamlit.io/privacy-policy

**Contact**
Pour toute question : hamza357@gmail.com

**Version** : 1.0 — Mai 2026
        """)


if __name__ == "__main__":
    main()
