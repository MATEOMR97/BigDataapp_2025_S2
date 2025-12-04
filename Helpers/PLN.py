import spacy
import nltk
from nltk.corpus import stopwords
from collections import Counter
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import pandas as pd
from datetime import datetime
import re
from typing import List, Dict, Tuple, Optional
import warnings

warnings.filterwarnings('ignore')

# Descargar recursos de NLTK si no están disponibles
try:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)
except Exception as e:
    print(f"Advertencia al descargar recursos NLTK: {e}")

class PLN:
    """Clase para procesamiento de lenguaje natural en español"""
    
    def __init__(self, modelo_spacy: str = 'es_core_news_lg', 
                 modelo_embeddings: str = 'paraphrase-multilingual-MiniLM-L12-v2',
                 cargar_modelos: bool = True):
        """
        Inicializa la clase PLN con los modelos necesarios
        """
        self.modelo_spacy_nombre = modelo_spacy
        self.modelo_embeddings_nombre = modelo_embeddings
        self.nlp = None
        self.model_embeddings = None
        self.stopwords_es = None
        
        if cargar_modelos:
            self._cargar_modelos()
    
    def _cargar_modelos(self):
        try:
            print("Cargando modelo de spaCy...")
            self.nlp = spacy.load(self.modelo_spacy_nombre)
            print(f"Modelo spaCy '{self.modelo_spacy_nombre}' cargado correctamente")
        except OSError:
            print(f"Error: Modelo '{self.modelo_spacy_nombre}' no encontrado.")
            print(f"Ejecuta: python -m spacy download {self.modelo_spacy_nombre}")
            print("Intentando cargar modelo básico de spaCy...")
            try:
                self.nlp = spacy.load('es_core_news_sm')
            except OSError:
                print("Error: No se pudo cargar ningún modelo de spaCy.")
                self.nlp = None

        try:
            print("Cargando modelo de embeddings...")
            self.model_embeddings = SentenceTransformer(self.modelo_embeddings_nombre)
            print(f"Modelo de embeddings '{self.modelo_embeddings_nombre}' cargado correctamente")
        except Exception as e:
            print(f"Error al cargar modelo de embeddings: {e}")
            self.model_embeddings = None

        try:
            self.stopwords_es = set(stopwords.words('spanish'))
        except LookupError:
            nltk.download('stopwords', quiet=True)
            self.stopwords_es = set(stopwords.words('spanish'))
    
    def extraer_entidades(self, texto: str) -> Dict[str, List[str]]:
        if not self.nlp:
            raise ValueError("Modelo de spaCy no está cargado. Llama a _cargar_modelos() primero.")
        
        doc = self.nlp(texto)
        entidades = {
            'personas': [],
            'lugares': [],
            'organizaciones': [],
            'fechas': [],
            'leyes': [],
            'otros': []
        }
        for ent in doc.ents:
            if ent.label_ == 'PER':
                entidades['personas'].append(ent.text)
            elif ent.label_ == 'LOC':
                entidades['lugares'].append(ent.text)
            elif ent.label_ == 'ORG':
                entidades['organizaciones'].append(ent.text)
            elif ent.label_ == 'DATE':
                entidades['fechas'].append(ent.text)
            elif ent.label_ == 'LAW' or 'ley' in ent.text.lower():
                entidades['leyes'].append(ent.text)
            else:
                entidades['otros'].append(f"{ent.text} ({ent.label_})")
        for key in entidades:
            entidades[key] = list(dict.fromkeys(entidades[key]))
        return entidades
    
    def extraer_temas(self, texto: str, top_n: int = 10) -> List[Tuple[str, float]]:
        if not self.nlp:
            raise ValueError("Modelo de spaCy no está cargado. Llama a _cargar_modelos() primero.")
        
        doc = self.nlp(texto)
        palabras_relevantes = []
        for token in doc:
            if (not token.is_stop and not token.is_punct and not token.is_space and
                    len(token.text) > 3 and token.pos_ in ['NOUN', 'PROPN', 'ADJ', 'VERB']):
                palabras_relevantes.append(token.lemma_.lower())
        contador = Counter(palabras_relevantes)
        temas = contador.most_common(top_n)
        total_palabras = len(palabras_relevantes)
        if total_palabras > 0:
            temas = [(palabra, (freq / total_palabras) * 100) for palabra, freq in temas]
        else:
            temas = [(palabra, 0.0) for palabra, freq in temas]
        return temas
    
    def generar_resumen(self, texto: str, num_oraciones: int = 3) -> str:
        if not self.nlp:
            raise ValueError("Modelo de spaCy no está cargado. Llama a _cargar_modelos() primero.")
        
        doc = self.nlp(texto)
        oraciones = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 20]
        if len(oraciones) <= num_oraciones:
            return ' '.join(oraciones)
        if len(oraciones) == 0:
            return texto[:200] + "..." if len(texto) > 200 else texto
        try:
            vectorizer = TfidfVectorizer(stop_words=list(self.stopwords_es))
            tfidf_matrix = vectorizer.fit_transform(oraciones)
            puntuaciones = np.array(tfidf_matrix.sum(axis=1)).flatten()
            indices_importantes = puntuaciones.argsort()[-num_oraciones:][::-1]
            indices_importantes = sorted(indices_importantes)
            resumen = ' '.join([oraciones[i] for i in indices_importantes])
            return resumen
        except Exception as e:
            print(f"Error al generar resumen: {e}")
            return ' '.join(oraciones[:num_oraciones])
    
    def calcular_similitud_semantica(self, textos: List[str]) -> pd.DataFrame:
        if not self.model_embeddings:
            raise ValueError("Modelo de embeddings no está cargado. Llama a _cargar_modelos() primero.")
        if len(textos) < 2:
            raise ValueError("Se necesitan al menos 2 textos para calcular similitud")
        embeddings = self.model_embeddings.encode(textos)
        similitud = cosine_similarity(embeddings)
        df = pd.DataFrame(
            similitud,
            columns=[f'Texto {i+1}' for i in range(len(textos))],
            index=[f'Texto {i+1}' for i in range(len(textos))]
        )
        return df
    
    def preprocesar_texto(self, texto: str, remover_stopwords: bool = True, lematizar: bool = True,
                          remover_numeros: bool = False, min_longitud: int = 3) -> str:
        if not self.nlp:
            raise ValueError("Modelo de spaCy no está cargado. Llama a _cargar_modelos() primero.")
        doc = self.nlp(texto)
        palabras_procesadas = []
        for token in doc:
            if len(token.text) < min_longitud:
                continue
            if remover_stopwords and token.is_stop:
                continue
            if token.is_punct or token.is_space:
                continue
            if remover_numeros and token.like_num:
                continue
            palabra = token.lemma_.lower() if lematizar else token.text.lower()
            palabras_procesadas.append(palabra)
        return ' '.join(palabras_procesadas)
    
    def analizar_sentimiento(self, texto: str, modelo: str = 'nlptown/bert-base-multilingual-uncased-sentiment') -> Dict:
        try:
            classifier = pipeline('sentiment-analysis', model=modelo, tokenizer=modelo)
            resultado = classifier(texto)
            return {
                'sentimiento': resultado[0]['label'],
                'score': resultado[0]['score']
            }
        except Exception as e:
            print(f"Error al analizar sentimiento: {e}")
            return {
                'sentimiento': 'ERROR',
                'score': 0.0,
                'error': str(e)
            }
    
    def extraer_nombres_propios(self, texto: str) -> List[str]:
        if not self.nlp:
            raise ValueError("Modelo de spaCy no está cargado. Llama a _cargar_modelos() primero.")
        doc = self.nlp(texto)
        nombres_propios = []
        for token in doc:
            if token.pos_ == 'PROPN' and len(token.text) > 2:
                nombres_propios.append(token.text)
        return list(dict.fromkeys(nombres_propios))
    
    def contar_palabras(self, texto: str, unicas: bool = False) -> int:
        if not self.nlp:
            raise ValueError("Modelo de spaCy no está cargado. Llama a _cargar_modelos() primero.")
        doc = self.nlp(texto)
        palabras = [token.text.lower() for token in doc if not token.is_punct and not token.is_space and not token.is_stop]
        if unicas:
            return len(set(palabras))
        return len(palabras)
    
    def close(self):
        """ Libera recursos de los modelos si se requiere """
        pass  # SpaCy y transformers gestionan la memoria automáticamente
