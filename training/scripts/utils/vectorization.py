"""TF-IDF vectorization and preprocessing utilities"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import MultiLabelBinarizer
import re

def create_tfidf_vectorizer():
    """
    Create TF-IDF vectorizer optimized for mental health text classification
    
    Configuration rationale:
      - max_features=8000: Captures diverse mental health vocabulary
      - ngram_range=(1,3): Unigrams, bigrams, trigrams (e.g., "panic attack")
      - min_df=3: Words must appear in >=3 docs (filter noise)
      - max_df=0.7: Ignore words in >70% of docs (too common)
      - sublinear_tf=True: Log scaling prevents term frequency dominance
    """
    return TfidfVectorizer(
        max_features=8000,
        ngram_range=(1, 3),
        min_df=3,
        max_df=0.7,
        sublinear_tf=True,
        strip_accents='unicode',
        lowercase=True,
        stop_words=None,  # Keep all words (mental health terms matter)
        token_pattern=r'\b\w+\b',
    )

def clean_text(text: str) -> str:
    """
    Minimal preprocessing (preserve mental health keywords)
    
    Only removes:
      - Excessive whitespace
      - URLs
      - Email addresses
    
    Keeps:
      - Punctuation (e.g., "I'm" → important context)
      - Numbers (e.g., "24/7 hotline")
      - Special chars in mental health terms
    """
    # Remove URLs
    text = re.sub(r'http\S+|www\.\S+', '', text)
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def prepare_multilabel_target(labels_list, categories):
    """
    Convert list of label lists to binary matrix
    
    Args:
        labels_list: [['depression', 'stress'], ['anxiety'], ...]
        categories: List of all 20 categories
    
    Returns:
        y: Binary matrix (n_samples, n_categories)
        mlb: Fitted MultiLabelBinarizer (for inverse_transform)
    
    Example:
        labels_list = [['depression', 'stress'], ['anxiety']]
        categories = ['anxiety', 'depression', 'stress', ...]
        
        Output y:
        [[0, 1, 1, 0, ...],  # depression=1, stress=1
         [1, 0, 0, 0, ...]]  # anxiety=1
    """
    mlb = MultiLabelBinarizer(classes=categories)
    y = mlb.fit_transform(labels_list)
    return y, mlb
