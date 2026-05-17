"""
GADIANI DJEN Proxy Server v2
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests, os, json

app = Flask(__name__)
CORS(app)

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
    return jsonify({"ok": True, "service": "Gadiani DJEN Proxy", "version": "2.0"})

@app.route("/diagnostico")
def diagnostico():
    """Testa a conexao com o PJe e mostra resposta bruta"""
    oab = request.args.get("oab", "425910")
    uf  = request.args.get("uf", "SP")
    ini = request.args.get("ini", "2026-05-14")
    fim = request.args.get("fim", "2026-05-16")

    url = PJE_BASE
    params = {
        "dataDisponibilizacaoInicio": ini,
        "dataDisponibilizacaoFim":    fim,
        "numeroOab": oab,
        "ufOab":     uf,
        "page":      0,
        "size":      5
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=20)
        try:
            body_json = r.json()
        except:
            body_json = None

        return jsonify({
            "ok":          True,
            "http_status": r.status_code,
            "url_chamada": r.url,
            "headers_resp": dict(r.headers),
            "body_raw":    r.text[:2000],
            "body_json":   body_json,
            "params_usados": params
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "params": params})

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
    debug = []

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
            r = requests.get(PJE_BASE, params=params, headers=HEADERS, timeout=20)
            debug.append(f"p{pagina}: HTTP {r.status_code}, url={r.url}")

            if r.status_code != 200:
                # Tentar ler o corpo mesmo com erro
                erros.append(f"p{pagina}: HTTP {r.status_code} corpo={r.text[:200]}")
                break

            raw = r.text.strip()
            debug.append(f"p{pagina}: body[100]={raw[:100]}")

            if not raw:
                erros.append(f"p{pagina}: resposta vazia")
                break

            data = r.json()

            # Suporte a varios formatos de resposta
            items = []
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                items = (data.get("content") or data.get("data") or
                         data.get("resultado") or data.get("result") or
                         data.get("comunicacoes") or [])

            debug.append(f"p{pagina}: {len(items)} itens encontrados")

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

            total_paginas = (data.get("totalPages") or data.get("totalPaginas") or
                            data.get("total_pages") or 1) if isinstance(data, dict) else 1
            pagina += 1

        except Exception as e:
            erros.append(f"p{pagina}: {str(e)}")
            debug.append(f"p{pagina}: EXCECAO {str(e)}")
            break

    return jsonify({
        "ok":    True,
        "data":  todas,
        "total": len(todas),
        "oab":   oab,
        "ini":   ini,
        "fim":   fim,
        "erros": erros,
        "debug": debug
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
