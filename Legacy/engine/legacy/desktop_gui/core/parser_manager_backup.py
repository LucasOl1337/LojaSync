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
            from parsers.marcas import tem_parser_para_marca, obter_parser_para_marca
            
            if not tem_parser_para_marca(marca):
                return None
            
            parser_modulo = obter_parser_para_marca(marca)
            if not parser_modulo or not hasattr(parser_modulo, 'processar_romaneio_completo'):
                return None
            
            print(f"🎯 Usando parser específico para marca: {marca}")
            resultado = parser_modulo.processar_romaneio_completo(
                arquivo_path,
                marca_override=marca,
                categoria_override=categoria
            )
            
            # Verificar se o parser encontrou produtos
            if self._parser_encontrou_produtos(resultado):
                return (resultado, f"Marca_{marca}")
            
            return None
            
        except Exception as e:
            print(f"⚠️ Erro no parser da marca {marca}: {e}")
            return None
    
    def _processar_pdf_padrao(self, arquivo_path, marca, categoria):
        """Processa PDF usando parsers padrão com fallback"""
        # 1. Tentar parser PDF especializado
        try:
            from parsers.parser_romaneio_pdf import processar_romaneio_completo
            print("📄 Usando parser PDF especializado...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            if self._parser_encontrou_produtos(resultado):
                return (resultado, "PDF_Especializado")
                
        except Exception as e:
            print(f"⚠️ Parser PDF especializado falhou: {e}")
        
        # 2. Fallback: Parser universal melhorado
        try:
            from parsers.parser_universal_melhorado import processar_romaneio_completo
            print("📄 Usando parser universal melhorado...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            return (resultado, "Universal_Melhorado")
            
        except Exception as e:
            return (f"❌ Erro em todos os parsers PDF: {e}", "Erro")
    
    def _processar_txt_padrao(self, arquivo_path, marca, categoria):
        """Processa TXT usando parsers padrão com fallback"""
        # 1. Tentar parser TXT especializado
        try:
            from parsers.parser_romaneio_txt import processar_romaneio_completo
            print("📄 Usando parser TXT especializado...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            if self._parser_encontrou_produtos(resultado):
                return (resultado, "TXT_Especializado")
                
        except Exception as e:
            print(f"⚠️ Parser TXT especializado falhou: {e}")
        
        # 2. Tentar parser universal original
        try:
            from parsers.parser_romaneio_universal import processar_romaneio_completo
            print("📄 Usando parser universal original...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            if self._parser_encontrou_produtos(resultado):
                return (resultado, "Universal_Original")
                
        except Exception as e:
            print(f"⚠️ Parser universal original falhou: {e}")
        
        # 3. Fallback final: Parser universal melhorado
        try:
            from parsers.parser_universal_melhorado import processar_romaneio_completo
            print("📄 Usando parser universal melhorado...")
            
            resultado = processar_romaneio_completo(
                arquivo_path,
                marca_override=marca or "OGOCHI",
                categoria_override=categoria or "Feminino"
            )
            
            return (resultado, "Universal_Melhorado")
            
        except Exception as e:
            return (f"❌ Erro em todos os parsers TXT: {e}", "Erro")
    
    def _parser_encontrou_produtos(self, resultado):
        """Verifica se o parser encontrou produtos válidos"""
        if not resultado:
            return False
        
        resultado_lower = resultado.lower()
        indicadores_falha = [
            "0 produtos encontrados",
            "nenhum produto",
            "erro",
            "falha",
            "não foi possível"
        ]
        
        return not any(indicador in resultado_lower for indicador in indicadores_falha)
    
    def listar_parsers_marca_disponiveis(self):
        """Lista todas as marcas que têm parsers específicos"""
        try:
            from parsers.marcas import listar_parsers_disponiveis
            return listar_parsers_disponiveis()
        except ImportError:
            return []

# Instância global do gerenciador
parser_manager = ParserManager()
