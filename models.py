from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Union

class EmbeddingModel:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EmbeddingModel, cls).__new__(cls)
        return cls._instance

    def load_model(self, model_name: str = "all-MiniLM-L6-v2"):
        if self._model is None:
            # print(f"Loading model {model_name}...")
            self._model = SentenceTransformer(model_name)
            # print("Model loaded.")

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        if self._model is None:
            self.load_model()
        return self._model.encode(texts, convert_to_numpy=True)

    def compute_similarity(self, text1: str, text2: str) -> float:
        emb1 = self.encode(text1)
        emb2 = self.encode(text2)
        return float(np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2)))

    def classify_intent(self, text: str, anchors: dict) -> str:
        """
        Classifies text against a dictionary of {label: anchor_text}.
        Returns the label with the highest similarity score if > threshold.
        """
        best_score = -1.0
        best_label = None
        
        text_emb = self.encode(text)
        
        for label, anchor_text in anchors.items():
            anchor_emb = self.encode(anchor_text)
            score = float(np.dot(text_emb, anchor_emb) / (np.linalg.norm(text_emb) * np.linalg.norm(anchor_emb)))
            
            if score > best_score:
                best_score = score
                best_label = label
                
        return best_label if best_score > 0.4 else None # Lower threshold for "soft" classification

    def get_sentiment_score(self, text: str) -> float:
        """
        Returns a sentiment score between -1 (negative) and 1 (positive).
        Uses simple anchor comparison.
        """
        positive_anchor = "Great, sounds good, excited, thanks, looking forward."
        negative_anchor = "Unsubscribe, stop, not interested, too expensive, bad, angry."
        
        pos_score = self.compute_similarity(text, positive_anchor)
        neg_score = self.compute_similarity(text, negative_anchor)
        
        return pos_score - neg_score
