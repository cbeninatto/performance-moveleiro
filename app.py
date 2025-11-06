import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

st.set_page_config(page_title="Relatório de Faturamento Extractor", page_icon="📄")
st.title("📄 Extrator de Relatório de Faturamento")

st.markdown("""
Envie o PDF do relatório e o sistema extrairá automaticamente os dados para **CSV** e **XLSX**.

Upload your billing report PDF below — it will extract product, month, quantity, and value into a clean CSV/XLSX.
""")

uploaded_file = st.file_uploader("📤 Escolha o arquivo PDF", type="pdf")


def br_to_float(s):
    return float(s.strip().replace(".", "").replace(",", "."))


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
            status_text.text(f"🔍 Processando página {i}/{total_pages}...")
            for raw in (page.extract_text() or "").splitlines():
                line = raw.strip()
                if not line or "Subtotal PRODUTO" in line or "www.kunden.com.br" in line:
                    continue
                if line.upper().startswith("PRODUTO:"):
                    m = prod_header_re.match(line)
                    if m:
                        current_code, current_desc = m.group(1).strip(), cleanup_re.sub("", m.group(2)).strip(" -")
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
                        pass
            progress_bar.progress(i / total_pages)

        status_text.text("✅ Processamento concluído.")

    if not records:
        st.error("Nenhum dado foi encontrado. Verifique se o PDF tem o formato esperado.")
    else:
        df = pd.DataFrame(records)
        st.success(f"✅ Extração concluída — {len(df)} linhas encontradas ({df['Codigo'].nunique()} produtos).")
        st.dataframe(df.head(20))

        # CSV
        csv_data = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Baixar CSV", csv_data, "relatorio_faturamento.csv", "text/csv")

        # XLSX
        xlsx_io = BytesIO()
        with pd.ExcelWriter(xlsx_io, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        st.download_button("⬇️ Baixar XLSX", xlsx_io.getvalue(), "relatorio_faturamento.xlsx", "application/vnd.ms-excel")
