"""Fix BBMNET scraper: filtrar por data de disputa futura ao inves de data publicacao"""
import os

path = r'C:\SGL-SISTEMA DE GESTAO DE LICITACOES\sgl\services\bbmnet_scraper.py'
lines = open(path, 'r', encoding='utf-8').readlines()

# Encontrar inicio e fim de buscar_todos_editais_uf
start = None
end = None
for i, line in enumerate(lines):
    if 'def buscar_todos_editais_uf(' in line:
        start = i
    if start and i > start and line.strip().startswith('# ====') and 'CONVERS' in line:
        end = i
        break

if not start or not end:
    print(f"ERRO: nao encontrei funcao. start={start} end={end}")
    exit(1)

print(f"Funcao encontrada: linhas {start+1} a {end}")

# Nova funcao
new_func = '''    def buscar_todos_editais_uf(
        self,
        uf: str,
        modalidade_id: int = 3,
        max_resultados: int = 3000,
        dias_recentes: int = 30,
    ) -> list:
        """
        Busca editais de uma UF com disputa futura (abertos).
        Pagina do mais recente ao mais antigo.
        Para quando encontra editais consecutivos ja encerrados.
        """
        from datetime import datetime, timedelta

        hoje = datetime.now()
        editais_abertos = []
        skip = 0
        take = 50
        encerrados_seguidos = 0
        max_encerrados_seguidos = 20  # Para de paginar apos 20 encerrados seguidos

        while skip < max_resultados:
            resultado = self.buscar_editais(
                uf=uf,
                modalidade_id=modalidade_id,
                take=take,
                skip=skip,
            )

            editais = resultado.get("editais", [])
            if not editais:
                break

            for edital in editais:
                # Verificar data de disputa/realizacao
                data_disputa_str = (
                    edital.get("dataRealizacao")
                    or edital.get("disputeStartDate")
                    or edital.get("publishAt")
                    or edital.get("createdAt")
                    or ""
                )

                # Verificar status
                status = edital.get("editalStatus", {})
                status_name = status.get("name", "") if isinstance(status, dict) else ""

                # Manter se:
                # 1. Status = Publicado (ainda aberto)
                # 2. OU data de disputa eh futura
                # 3. OU publicado nos ultimos N dias (fallback)
                manter = False

                if status_name.lower() in ["publicado", "aberto", "em andamento"]:
                    manter = True
                    encerrados_seguidos = 0

                if not manter and data_disputa_str:
                    try:
                        data_disputa = datetime.fromisoformat(
                            data_disputa_str.replace("Z", "").split("+")[0]
                        )
                        if data_disputa >= hoje:
                            manter = True
                            encerrados_seguidos = 0
                    except (ValueError, TypeError):
                        pass

                if not manter:
                    # Fallback: publicado nos ultimos N dias
                    pub_str = edital.get("publishAt") or edital.get("createdAt") or ""
                    if pub_str:
                        try:
                            pub_date = datetime.fromisoformat(
                                pub_str.replace("Z", "").split("+")[0]
                            )
                            data_corte = hoje - timedelta(days=dias_recentes)
                            if pub_date >= data_corte:
                                manter = True
                                encerrados_seguidos = 0
                        except (ValueError, TypeError):
                            pass

                if manter:
                    editais_abertos.append(edital)
                else:
                    encerrados_seguidos += 1

            skip += take

            # Rate limiting
            time.sleep(0.3)

            # Parar se muitos encerrados seguidos (ja passou dos abertos)
            if encerrados_seguidos >= max_encerrados_seguidos:
                logger.info(
                    f"BBMNET UF={uf}: parando apos {encerrados_seguidos} "
                    f"encerrados seguidos (skip={skip})"
                )
                break

            # Se recebeu menos que o pedido, acabou
            if len(editais) < take:
                break

        logger.info(
            f"BBMNET UF={uf}: {len(editais_abertos)} editais abertos "
            f"(paginados ate skip={skip})"
        )
        return editais_abertos

'''

# Substituir
result = lines[:start] + [new_func] + lines[end:]
open(path, 'w', encoding='utf-8').writelines(result)
print(f"OK - buscar_todos_editais_uf reescrita (linhas {start+1}-{end})")
print(f"  - Filtro: data_disputa >= hoje OU status=Publicado OU publicado ultimos N dias")
print(f"  - max_resultados: 3000")
print(f"  - Para apos 20 encerrados seguidos")
