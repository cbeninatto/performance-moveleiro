import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import time

st.set_page_config(page_title="Relatório de Faturamento Extractor", page_icon="📄")
st.title("📄 Extrator de Relatório de Faturamento")

st.markdown("""
Envie o PDF completo do relatório de faturamento e o sistema extrairá automaticamente os dados para **CSV** e **XLSX**, incluindo a **categoria de cada produto** para verificação.

Upload your complete billing report PDF below — the system will automatically extract and classify data into clean **CSV** and **XLSX** files.
""")

uploaded_file = st.file_uploader("📤 Escolha o arquivo PDF", type="pdf")


def br_to_float(s):
    return float(s.strip().replace(".", "").replace(",", "."))


# --- Classification function ---
def map_categoria(desc: str) -> str:
    d = (desc or "").upper()

    # Corrediça Oculta
    if ("ESCOND" in d or "SLIM MV119" in d or "DREAM BOX" in d or "OPENBOX" in d
        or ("GAVETA" in d and ("BOX" in d or "OPENBOX" in d))):
        return "Corrediça Oculta"

    # Corrediça Telescópica
    if ("TRILHO LIGHT" in d or "TRILHO LIFE" in d or "TRILHO MOVE" in d or "TRILHO LIGTH" in d
        or ("TRILHO" in d and ("NORMAL" in d or "TELE" in d))):
        return "Corrediça Telescópica"

    # Dobradiça / Pistão
    if "DOBRADI" in d or "HINGE" in d or "PISTAO" in d or "AMORTECEDOR" in d:
        return "Dobradiça / Pistão"

    # Acessórios
    if ("SUPORTE" in d or "CANTONEIRA" in d or "PLACA" in d
        or "FIXAÇÃO" in d or "FIXACAO" in d or "PARAFUSO" in d):
        return "Acessório"

    return "Outros"


# --- Regex definitions ---
prod_header_re = re.compile(r"^\s*PRODUTO:\s*(\d+)\s*-\s*(.+?)\s*$", re.IGNORECASE)
cleanup_re = re.compile(r"\s*Quantidade\s*%\s*Quantidade\s*Valor\s*%\s*Valor\s*$", re.IGNORECASE)
mes_line_re = re.compile(
    r"^\s*MÊS\s*:\s*(\d{2})/(\d{4}).*?\s([\d\.\,]+)\s+[\d\.\,]+%\s+([\d\.\,]+)\s+[\d\.\,]+%",
    re.IGNORECASE,
)


if uploaded_file:
    records, current_code, current_desc = [], None, None
    with pdfplumber.open(uploaded_file) as pdf:
        total_pages = len(pdf.pages)
        st.info(f"📄 PDF carregado com **{total_pages} páginas**.")
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, page in enumerate(pdf.pages, start=1):
            status_text.text(f"🔍 Lendo página {i}/{total_pages}...")
            for raw in (page.extract_text() or "").splitlines():
                line = raw.strip()
                if not line or "Subtotal PRODUTO" in line or "www.kunden.com.br" in line:
                    continue
                if line.upper().startswith("PRODUTO:"):
                    m = prod_header_re.match(line)
                    if m:
                        current_code, current_desc = (
                            m.group(1).strip(),
                            cleanup_re.sub("", m.group(2)).strip(" -"),
                        )
                    continue
                m2 = mes_line_re.match(line)
                if m2 and current_code:
                    mes, ano, qty, val = m2.groups()
                    try:
                        records.append({
                            "Codigo": current_code,
                            "Descricao": current_desc,
                            "Quantidade": br_to_float(qty),
                            "Valor": br_to_float(val),
                            "Mes": int(mes),
                            "Ano": int(ano),
                        })
                    except Exception:
                        # Se der erro em alguma linha, simplesmente pula
                        pass
            progress_bar.progress(i / total_pages)
            time.sleep(0.02)

        status_text.text("📘 Leitura concluída — processando dados...")

    if not records:
        st.error("Nenhum dado foi encontrado. Verifique se o PDF tem o formato esperado.")
    else:
        # Cria DataFrame
        df = pd.DataFrame(records)

        # 🔴 AQUI garantimos a criação da coluna Categoria
        df["Categoria"] = df["Descricao"].apply(map_categoria)

        # Pequeno debug visual para você conferir as colunas
        st.caption("Colunas geradas: " + ", ".join(df.columns))

        st.success(
            f"✅ Extração concluída — {len(df)} linhas "
            f"({df['Codigo'].nunique()} produtos)."
        )
        st.dataframe(df.head(20))

        # CSV (com Categoria inclusa)
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Baixar CSV",
            csv_data,
            "relatorio_faturamento.csv",
            "text/csv",
        )

        # XLSX (com Categoria inclusa)
        xlsx_io = BytesIO()
        with pd.ExcelWriter(xlsx_io, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            "⬇️ Baixar XLSX",
            xlsx_io.getvalue(),
            "relatorio_faturamento.xlsx",
            "application/vnd.ms-excel",
        )

        st.info("📊 Arquivos prontos para download (incluindo coluna **Categoria**).")
