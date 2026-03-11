"""
Gerenciador de Parsers com Priorização por Marca

Este módulo gerencia a seleção e execução de parsers, priorizando parsers específicos 
por marca quando disponíveis, com fallback para parsers padrão.
"""

import os
from pathlib import Path

class ParserManager:
    """Gerenciador inteligente de parsers com priorização por marca"""
    
    def __init__(self):
        self.parsers_marca_cache = {}
    
    def processar_romaneio(self, arquivo_path, marca=None, categoria=None):
        """
        Processa romaneio priorizando parser específico da marca
        
        Args:
            arquivo_path: Caminho para o arquivo do romaneio
            marca: Marca selecionada (ex: "OGOCHI", "MALWEE")
            categoria: Categoria selecionada (ex: "Feminino", "Masculino")
            
        Returns:
            tuple: (resultado_processamento, parser_usado)
        """
        arquivo_lower = arquivo_path.lower()
        
        # 0. NOVO PRINCIPAL: Tentar SongBird primeiro (parser orquestrador)
        try:
            from parsers.parser_SongBird import processar_romaneio_completo as songbird_process
            print("[ParserManager] Tentando parser SongBird...")
            resultado_sb = songbird_process(
                arquivo_path,
                marca_override=marca,
                categoria_override=categoria
            )
            if self._parser_encontrou_produtos(resultado_sb):
                print("DEBUG: SongBird teve sucesso!")
                return (resultado_sb, "SongBird")
            else:
                print("[ParserManager] SongBird não encontrou produtos, usando fallback...")
        except Exception as e:
            print(f"[ParserManager] SongBird falhou: {e}")
        
        # 1. PRIORIDADE: Tentar parser específico da marca
        if marca:
            resultado_marca = self._tentar_parser_marca(arquivo_path, marca, categoria)
            if resultado_marca:
                return resultado_marca
        
        # 2. FALLBACK: Usar parsers padrão baseado no tipo de arquivo
        if arquivo_lower.endswith('.pdf'):
            return self._processar_pdf_padrao(arquivo_path, marca, categoria)
        else:
            return self._processar_txt_padrao(arquivo_path, marca, categoria)
    
    def _tentar_parser_marca(self, arquivo_path, marca, categoria):
        """Tenta usar parser específico da marca"""
        try:
            print(f"DEBUG: Tentando parser para marca: {marca}")
            from parsers.marcas import tem_parser_para_marca, obter_parser_para_marca
            
            print(f"DEBUG: Import realizado com sucesso")
            
            if not tem_parser_para_marca(marca):
                print(f"DEBUG: Nao tem parser para marca {marca}")
                return None
            
            print(f"DEBUG: Parser encontrado para marca {marca}")
            
            parser_modulo = obter_parser_para_marca(marca)
            if not parser_modulo or not hasattr(parser_modulo, 'processar_romaneio_completo'):
                print(f"DEBUG: Modulo do parser invalido ou sem funcao processar_romaneio_completo")
                return None
            
            print(f"Usando parser especifico para marca: {marca}")
            resultado = parser_modulo.processar_romaneio_completo(
                arquivo_path,
                marca_override=marca,
                categoria_override=categoria
            )
            
            print(f"DEBUG: Resultado do parser {marca}: {resultado[:100]}...")
            
            # Verificar se o parser encontrou produtos
            if self._parser_encontrou_produtos(resultado):
                print(f"DEBUG: Parser {marca} teve sucesso!")
                return (resultado, f"Marca_{marca}")
            
            print(f"DEBUG: Parser {marca} nao encontrou produtos validos")
            return None
            
        except Exception as e:
            print(f"Erro no parser da marca {marca}: {e}")
            import traceback
            print(f"DEBUG: Traceback completo: {traceback.format_exc()}")
            return None
    
    def _processar_pdf_padrao(self, arquivo_path, marca, categoria):
        """Processa PDF usando parsers padrão com fallback"""
        # 1. Tentar parser PDF especializado
        try:
            from parsers.parser_romaneio_pdf import processar_romaneio_completo
            print("[ParserManager] Usando parser PDF especializado...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            if self._parser_encontrou_produtos(resultado):
                return (resultado, "PDF_Especializado")
                
        except Exception as e:
            print(f"[ParserManager] Parser PDF especializado falhou: {e}")
        
        return ("❌ SongBird e parsers PDF legados não processaram este romaneio. Ajuste necessário.", "Erro")
    
    def _processar_txt_padrao(self, arquivo_path, marca, categoria):
        """Processa TXT usando parsers padrão com fallback"""
        # 1. Tentar parser TXT especializado
        try:
            from parsers.parser_romaneio_txt import processar_romaneio_completo
            print("[ParserManager] Usando parser TXT especializado...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            if self._parser_encontrou_produtos(resultado):
                return (resultado, "TXT_Especializado")
                
        except Exception as e:
            print(f"[ParserManager] Parser TXT especializado falhou: {e}")
        
        # 2. Tentar parser universal original
        try:
            from parsers.parser_romaneio_universal import processar_romaneio_completo
            print("[ParserManager] Usando parser universal original...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            if self._parser_encontrou_produtos(resultado):
                return (resultado, "Universal_Original")
                
        except Exception as e:
            print(f"[ParserManager] Parser universal original falhou: {e}")
        
        return ("❌ SongBird e parsers TXT legados não processaram este romaneio. Ajuste necessário.", "Erro")
    
    def _parser_encontrou_produtos(self, resultado):
        """Verifica se o parser encontrou produtos válidos"""
        if not resultado:
            return False
        
        # Debug: Mostrar resultado para diagnóstico
        print(f"DEBUG: Verificando resultado do parser: {resultado[:200]}...")
        
        resultado_lower = resultado.lower()
        
        # Verificar indicadores de sucesso primeiro
        indicadores_sucesso = [
            "produtos encontrados",
            "produto",
            "processado com sucesso",
            "parser:",
            "encontrados"
        ]
        
        tem_sucesso = any(indicador in resultado_lower for indicador in indicadores_sucesso)
        
        # Verificar indicadores de falha
        indicadores_falha = [
            "0 produtos encontrados",
            "nenhum produto encontrado",
            "erro",
            "falha",
            "nao foi possivel"
        ]
        
        tem_falha = any(indicador in resultado_lower for indicador in indicadores_falha)
        
        # Priorizar indicadores de sucesso
        if tem_sucesso and not tem_falha:
            print(f"DEBUG: Parser encontrou produtos - sucesso detectado")
            return True
        elif tem_falha:
            print(f"DEBUG: Parser falhou - falha detectada")
            return False
        else:
            # Se não tem indicadores claros, assumir sucesso se há conteúdo
            resultado_valido = len(resultado.strip()) > 50
            print(f"DEBUG: Resultado ambiguo - assumindo {'sucesso' if resultado_valido else 'falha'}")
            return resultado_valido
    
    def listar_parsers_marca_disponiveis(self):
        """Lista todas as marcas que têm parsers específicos"""
        try:
            from parsers.marcas import listar_parsers_disponiveis
            return listar_parsers_disponiveis()
        except ImportError:
            return []

# Instância global do gerenciador
parser_manager = ParserManager()
