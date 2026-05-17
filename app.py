"""
GADIANI DJEN Proxy Server
Deploy no Render.com (free tier) - busca publicacoes PJe sem restricao CORS
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, os

app = Flask(__name__)
CORS(app)  # permite qualquer origem

PJE_BASE = "https://comunica.pje.jus.br/api/v1/comunicacao"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://comunica.pje.jus.br/",
    "Origin": "https://comunica.pje.jus.br"
}

@app.route("/")
def index():
    return jsonify({"ok": True, "service": "Gadiani DJEN Proxy", "version": "1.0"})

@app.route("/djen")
def djen():
    oab = request.args.get("oab", "")
    uf  = request.args.get("uf", "SP")
    ini = request.args.get("ini", "")
    fim = request.args.get("fim", ini)

    if not oab or not ini:
        return jsonify({"ok": False, "error": "oab e ini sao obrigatorios"})

    todas = []
    pagina = 0
    total_paginas = 1
    erros = []

    while pagina < total_paginas and pagina < 50:
        params = {
            "dataDisponibilizacaoInicio": ini,
            "dataDisponibilizacaoFim":    fim,
            "numeroOab": oab,
            "ufOab":     uf,
            "page":      pagina,
            "size":      20
        }
        try:
            r = requests.get(PJE_BASE, params=params, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                erros.append(f"p{pagina}: HTTP {r.status_code}")
                break
            data = r.json()
            items = (data.get("content") or data.get("data") or
                     data.get("resultado") or (data if isinstance(data, list) else []))
            for it in items:
                todas.append({
                    "id":              str(it.get("id") or it.get("idComunicacao") or f"{oab}_{pagina}_{len(todas)}"),
                    "numeroProcesso":  it.get("numeroProcessoTrf") or it.get("numeroProcesso") or it.get("numero") or "",
                    "nomeParte":       it.get("nomeAdvogado") or it.get("destinatario") or it.get("parte") or "",
                    "texto":           it.get("texto") or it.get("conteudo") or it.get("teor") or "",
                    "tipoDoDocumento": it.get("tipoComunicacao") or it.get("tipoDocumento") or it.get("tipo") or "",
                    "siglaTribunal":   it.get("siglaTribunal") or it.get("tribunal") or "PJe",
                    "linkTribunal":    it.get("linkPortal") or it.get("link") or "",
                    "oab": oab, "uf": uf,
                    "dataDisponibilizacao": it.get("dataDisponibilizacao") or ini
                })
            total_paginas = data.get("totalPages") or data.get("totalPaginas") or 1
            pagina += 1
        except Exception as e:
            erros.append(f"p{pagina}: {str(e)}")
            break

    return jsonify({
        "ok":    True,
        "data":  todas,
        "total": len(todas),
        "oab":   oab,
        "ini":   ini,
        "fim":   fim,
        "erros": erros
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
