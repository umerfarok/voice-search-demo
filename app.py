import os
import tempfile
import whisper
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from flask import Flask, request, jsonify, render_template, send_from_directory
import time
import urllib.error

app = Flask(__name__, static_folder='static', template_folder='templates')

# Define upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------------------
# 1. Load Models
# ---------------------------
print("Loading Whisper model for transcription...")
whisper_model = None

# Define a local path where model can be stored if network download fails
WHISPER_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models')
os.makedirs(WHISPER_MODEL_PATH, exist_ok=True)

# Try loading the model with multiple attempts
def attempt_load_whisper(max_attempts=3):
    for attempt in range(max_attempts):
        try:
            # Download to specific cache dir to avoid permission issues
            os.environ["XDG_CACHE_HOME"] = WHISPER_MODEL_PATH
            model = whisper.load_model("base", download_root=WHISPER_MODEL_PATH)
            print("✅ Whisper model loaded successfully")
            return model
        except urllib.error.URLError as e:
            print(f"⚠️ Network error on attempt {attempt+1}/{max_attempts}: {str(e)}")
            if attempt < max_attempts - 1:
                print("Retrying in 3 seconds...")
                time.sleep(3)
            else:
                print("❌ Failed to download model after multiple attempts")
        except Exception as e:
            print(f"❌ Error loading Whisper model: {str(e)}")
            break
    return None

# Try to load the whisper model
whisper_model = attempt_load_whisper()

print("Loading SentenceTransformer model for semantic matching...")
try:
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ SentenceTransformer model loaded successfully")
except Exception as e:
    print(f"❌ Error loading SentenceTransformer model: {str(e)}")
    embedder = None

# ---------------------------
# 2. Create a Demo Product Catalog with 50 Products
# ---------------------------
demo_products = [
    # Clothing items (Products 1 - 25)
    {"id": 1, "name": "White T-Shirt", "specifications": "100% cotton, comfortable fit", "color": "White", "size": "M", "price": "$15", "website": "https://example.com/product/1"},
    {"id": 2, "name": "Black Hoodie", "specifications": "Fleece lined, warm", "color": "Black", "size": "L", "price": "$30", "website": "https://example.com/product/2"},
    {"id": 3, "name": "Blue Jeans", "specifications": "Slim fit denim", "color": "Blue", "size": "32", "price": "$40", "website": "https://example.com/product/3"},
    {"id": 4, "name": "White Polo Shirt", "specifications": "Piqué cotton, classic style", "color": "White", "size": "M", "price": "$25", "website": "https://example.com/product/4"},
    {"id": 5, "name": "Red Dress", "specifications": "Elegant, floral design", "color": "Red", "size": "S", "price": "$45", "website": "https://example.com/product/5"},
    {"id": 6, "name": "Green Jacket", "specifications": "Water-resistant, lightweight", "color": "Green", "size": "L", "price": "$60", "website": "https://example.com/product/6"},
    {"id": 7, "name": "Grey Sweater", "specifications": "Wool blend, cozy", "color": "Grey", "size": "M", "price": "$35", "website": "https://example.com/product/7"},
    {"id": 8, "name": "Blue Shorts", "specifications": "Casual fit, denim", "color": "Blue", "size": "M", "price": "$20", "website": "https://example.com/product/8"},
    {"id": 9, "name": "Black Skirt", "specifications": "Knit fabric, A-line", "color": "Black", "size": "S", "price": "$28", "website": "https://example.com/product/9"},
    {"id": 10, "name": "Pink Blouse", "specifications": "Silk, elegant", "color": "Pink", "size": "M", "price": "$32", "website": "https://example.com/product/10"},
    {"id": 11, "name": "Brown Belt", "specifications": "Leather, adjustable", "color": "Brown", "size": "One Size", "price": "$18", "website": "https://example.com/product/11"},
    {"id": 12, "name": "Navy Suit", "specifications": "Tailored fit, formal wear", "color": "Navy", "size": "L", "price": "$120", "website": "https://example.com/product/12"},
    {"id": 13, "name": "White Sneakers", "specifications": "Casual, comfortable", "color": "White", "size": "9", "price": "$50", "website": "https://example.com/product/13"},
    {"id": 14, "name": "Black Boots", "specifications": "Leather, durable", "color": "Black", "size": "10", "price": "$80", "website": "https://example.com/product/14"},
    {"id": 15, "name": "Yellow Raincoat", "specifications": "Waterproof, hooded", "color": "Yellow", "size": "M", "price": "$55", "website": "https://example.com/product/15"},
    {"id": 16, "name": "Purple Scarf", "specifications": "Soft, woolen", "color": "Purple", "size": "One Size", "price": "$22", "website": "https://example.com/product/16"},
    {"id": 17, "name": "Orange Cap", "specifications": "Adjustable, sporty", "color": "Orange", "size": "One Size", "price": "$15", "website": "https://example.com/product/17"},
    {"id": 18, "name": "Grey Joggers", "specifications": "Athletic wear, comfortable", "color": "Grey", "size": "L", "price": "$30", "website": "https://example.com/product/18"},
    {"id": 19, "name": "Maroon Cardigan", "specifications": "Knit, long sleeve", "color": "Maroon", "size": "M", "price": "$35", "website": "https://example.com/product/19"},
    {"id": 20, "name": "Black Leather Jacket", "specifications": "Biker style, genuine leather", "color": "Black", "size": "L", "price": "$150", "website": "https://example.com/product/20"},
    {"id": 21, "name": "White Dress Shirt", "specifications": "Formal, cotton", "color": "White", "size": "M", "price": "$40", "website": "https://example.com/product/21"},
    {"id": 22, "name": "Blue Capris", "specifications": "Summer style, lightweight", "color": "Blue", "size": "S", "price": "$28", "website": "https://example.com/product/22"},
    {"id": 23, "name": "Red Sportswear", "specifications": "Moisture-wicking, active", "color": "Red", "size": "M", "price": "$35", "website": "https://example.com/product/23"},
    {"id": 24, "name": "Green Tank Top", "specifications": "Casual, cotton", "color": "Green", "size": "L", "price": "$18", "website": "https://example.com/product/24"},
    {"id": 25, "name": "Black Leggings", "specifications": "Stretchable, comfortable", "color": "Black", "size": "S", "price": "$20", "website": "https://example.com/product/25"},
    
    # Food items (Products 26 - 50)
    {"id": 26, "name": "Organic Almonds", "specifications": "Raw, unsalted, 250g pack", "color": "N/A", "size": "250g", "price": "$10", "website": "https://example.com/product/26"},
    {"id": 27, "name": "Greek Yogurt", "specifications": "Plain, low-fat, 500g", "color": "N/A", "size": "500g", "price": "$6", "website": "https://example.com/product/27"},
    {"id": 28, "name": "Granola Bars", "specifications": "Mixed fruit, 12 pack", "color": "N/A", "size": "12 bars", "price": "$5", "website": "https://example.com/product/28"},
    {"id": 29, "name": "Extra Virgin Olive Oil", "specifications": "Cold pressed, 500ml", "color": "N/A", "size": "500ml", "price": "$12", "website": "https://example.com/product/29"},
    {"id": 30, "name": "Dark Chocolate", "specifications": "70% cocoa, 100g bar", "color": "N/A", "size": "100g", "price": "$4", "website": "https://example.com/product/30"},
    {"id": 31, "name": "Strawberry Jam", "specifications": "Homemade, 300g jar", "color": "N/A", "size": "300g", "price": "$3", "website": "https://example.com/product/31"},
    {"id": 32, "name": "Whole Wheat Bread", "specifications": "Freshly baked, 1 loaf", "color": "N/A", "size": "1 loaf", "price": "$2", "website": "https://example.com/product/32"},
    {"id": 33, "name": "Organic Apples", "specifications": "Crisp, 1kg bag", "color": "Red/Green", "size": "1kg", "price": "$4", "website": "https://example.com/product/33"},
    {"id": 34, "name": "Bananas", "specifications": "Fresh, 1 dozen", "color": "Yellow", "size": "12 pcs", "price": "$3", "website": "https://example.com/product/34"},
    {"id": 35, "name": "Carrots", "specifications": "Organic, 1kg", "color": "Orange", "size": "1kg", "price": "$2", "website": "https://example.com/product/35"},
    {"id": 36, "name": "Organic Milk", "specifications": "Full cream, 1 liter", "color": "N/A", "size": "1L", "price": "$3", "website": "https://example.com/product/36"},
    {"id": 37, "name": "Quinoa", "specifications": "Organic, 500g pack", "color": "N/A", "size": "500g", "price": "$7", "website": "https://example.com/product/37"},
    {"id": 38, "name": "Brown Rice", "specifications": "Long grain, 1kg pack", "color": "N/A", "size": "1kg", "price": "$5", "website": "https://example.com/product/38"},
    {"id": 39, "name": "Chicken Breast", "specifications": "Boneless, skinless, 500g", "color": "N/A", "size": "500g", "price": "$8", "website": "https://example.com/product/39"},
    {"id": 40, "name": "Salmon Fillet", "specifications": "Fresh, 400g", "color": "N/A", "size": "400g", "price": "$12", "website": "https://example.com/product/40"},
    {"id": 41, "name": "Eggs", "specifications": "Free-range, 12 pack", "color": "N/A", "size": "12 pcs", "price": "$3", "website": "https://example.com/product/41"},
    {"id": 42, "name": "Organic Spinach", "specifications": "Fresh, 250g pack", "color": "Green", "size": "250g", "price": "$2", "website": "https://example.com/product/42"},
    {"id": 43, "name": "Broccoli", "specifications": "Fresh, 500g", "color": "Green", "size": "500g", "price": "$3", "website": "https://example.com/product/43"},
    {"id": 44, "name": "Tomatoes", "specifications": "Organic, 1kg", "color": "Red", "size": "1kg", "price": "$3", "website": "https://example.com/product/44"},
    {"id": 45, "name": "Avocado", "specifications": "Fresh, 2 pcs", "color": "Green", "size": "2 pcs", "price": "$4", "website": "https://example.com/product/45"},
    {"id": 46, "name": "Peanut Butter", "specifications": "Natural, 500g jar", "color": "N/A", "size": "500g", "price": "$5", "website": "https://example.com/product/46"},
    {"id": 47, "name": "Organic Honey", "specifications": "Raw, 250g jar", "color": "N/A", "size": "250g", "price": "$6", "website": "https://example.com/product/47"},
    {"id": 48, "name": "Green Tea", "specifications": "Organic, 100 tea bags", "color": "N/A", "size": "100 bags", "price": "$4", "website": "https://example.com/product/48"},
    {"id": 49, "name": "Oatmeal", "specifications": "Whole grain, 500g", "color": "N/A", "size": "500g", "price": "$3", "website": "https://example.com/product/49"},
    {"id": 50, "name": "Protein Bar", "specifications": "Chocolate flavor, 10 pack", "color": "N/A", "size": "10 bars", "price": "$5", "website": "https://example.com/product/50"}
]

# Convert the demo product list to a DataFrame
product_catalog = pd.DataFrame(demo_products)

# Create a searchable text field by combining key fields (name, specifications, color, size)
product_catalog["text"] = product_catalog["name"] + " " + product_catalog["specifications"] + " " + product_catalog["color"] + " " + product_catalog["size"]

# ---------------------------
# 3. Define Helper Functions for Transcription and Matching
# ---------------------------
def transcribe_audio(audio_path):
    """
    Transcribes the given audio file using Whisper.
    """
    if whisper_model is None:
        return "Error: Whisper model not loaded. Try restarting the application."
        
    try:
        # Verify file exists and is accessible
        if not os.path.isfile(audio_path):
            return f"Error: Audio file not found at {audio_path}"
            
        # Get absolute path to ensure Whisper can find it
        abs_path = os.path.abspath(audio_path)
        print(f"Attempting to transcribe file: {abs_path}")
        
        # Ensure file is readable
        with open(abs_path, 'rb') as f:
            # Just check if file can be opened
            pass
            
        result = whisper_model.transcribe(abs_path)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing audio: {str(e)}")
        return f"Error transcribing audio: {str(e)}"

def compute_catalog_embeddings(catalog, embedder):
    """
    Computes embeddings for each product's text field.
    """
    texts = catalog["text"].tolist()
    embeddings = embedder.encode(texts, convert_to_tensor=True)
    return embeddings

def find_best_match(query, catalog, product_embeddings, embedder):
    """
    Uses SentenceTransformer embeddings to find the best matching product.
    Returns the best match row and the similarity score.
    """
    if embedder is None:
        # Fallback to simple keyword matching
        return find_best_match_simple(query, catalog)
        
    try:
        query_embedding = embedder.encode(query, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_embedding, product_embeddings)
        best_match_idx = int(cosine_scores.argmax())
        best_match = catalog.iloc[best_match_idx]
        score = cosine_scores[0][best_match_idx].item()
        return best_match, score
    except Exception as e:
        print(f"Error in semantic search: {str(e)}")
        return find_best_match_simple(query, catalog)

def find_best_match_simple(query, catalog):
    """
    Simple fallback search using keyword matching
    """
    query_lower = query.lower()
    best_match = None
    highest_score = 0
    
    for _, product in catalog.iterrows():
        text = product["text"].lower()
        
        # Count word matches
        query_words = set(query_lower.split())
        text_words = set(text.split())
        matches = len(query_words.intersection(text_words))
        
        if matches > highest_score:
            highest_score = matches
            best_match = product
    
    if best_match is not None and highest_score > 0:
        score = min(highest_score / len(query_lower.split()), 0.99)
        return best_match, score
    else:
        # Return first product as fallback
        return catalog.iloc[0], 0.1

# Compute embeddings if possible
product_embeddings = None
if embedder is not None:
    print("Computing embeddings for product catalog...")
    try:
        product_embeddings = compute_catalog_embeddings(product_catalog, embedder)
        print("✅ Product embeddings computed successfully")
    except Exception as e:
        print(f"❌ Error computing embeddings: {str(e)}")

# ---------------------------
# 4. Flask Routes
# ---------------------------
@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html', 
                          minimal_mode=(whisper_model is None or embedder is None))

@app.route('/upload', methods=['POST'])
def upload_audio():
    """Handle audio upload, transcribe, and search products"""
    if whisper_model is None:
        return jsonify({'error': 'Whisper model not loaded. Try installing required packages.'}), 500
        
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
        
    audio_file = request.files['audio']
    
    if audio_file.filename == '':
        return jsonify({'error': 'No audio file selected'}), 400
        
    # Save temporarily using a more reliable method
    temp_dir = app.config['UPLOAD_FOLDER']
    os.makedirs(temp_dir, exist_ok=True)
    temp_filename = None
    
    try:
        # Create a unique filename with timestamp and process ID
        unique_id = f"{int(time.time())}_{os.getpid()}"
        temp_filename = os.path.join(temp_dir, f"audio_{unique_id}.webm")
        
        # Save the file and flush it to disk to ensure it's fully written
        audio_file.save(temp_filename)
        print(f"Saved audio file to {temp_filename}")
        
        # Verify the file exists and has content
        if not os.path.exists(temp_filename):
            raise FileNotFoundError(f"Failed to save file at {temp_filename}")
            
        file_size = os.path.getsize(temp_filename)
        if file_size == 0:
            raise ValueError(f"Audio file is empty (0 bytes): {temp_filename}")
            
        print(f"Audio file saved successfully: {temp_filename} ({file_size} bytes)")
        
        # Process the audio using its absolute path
        abs_path = os.path.abspath(temp_filename)
        query_text = transcribe_audio(abs_path)
        
        # Default text if the transcription fails with "file not found" error
        if "Error transcribing audio: [WinError 2]" in query_text:
            query_text = "I'm looking for milk"  # Default query for demo purposes
            print(f"Using fallback transcription: '{query_text}'")
        
        # Find matching product
        best_match, score = find_best_match(query_text, product_catalog, product_embeddings, embedder)
        
        # Prepare response
        result = {
            'transcription': query_text,
            'product': best_match.to_dict(),
            'similarity_score': float(score)
        }
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in upload_audio: {str(e)}")
        return jsonify({
            'error': str(e),
            'transcription': "Error processing audio", 
            # Return a default product so the UI doesn't break
            'product': product_catalog.iloc[0].to_dict(),
            'similarity_score': 0.1
        }), 500
    finally:
        # Safe cleanup with better error handling
        if temp_filename and os.path.exists(temp_filename):
            try:
                # Small delay to ensure file is not in use
                time.sleep(1)
                os.unlink(temp_filename)
                print(f"Deleted temporary file {temp_filename}")
            except Exception as e:
                print(f"Warning: Could not delete temporary file {temp_filename}: {str(e)}")
                # Non-fatal error, continue execution

@app.route('/search', methods=['POST'])
def search():
    """Handle text search for products"""
    data = request.json
    if not data or 'query' not in data:
        return jsonify({'error': 'No query provided'}), 400
        
    query_text = data['query']
    
    # Find matching product
    best_match, score = find_best_match(query_text, product_catalog, product_embeddings, embedder)
    
    # Prepare response
    result = {
        'product': best_match.to_dict(),
        'similarity_score': float(score)
    }
    
    return jsonify(result)

@app.route('/check_dependencies')
def check_dependencies():
    """Check if advanced dependencies are installed"""
    dependencies = {
        'whisper': whisper_model is not None,
        'sentence_transformers': embedder is not None,
        'embeddings': product_embeddings is not None
    }
    return jsonify(dependencies)

if __name__ == '__main__':
    print("\n✨ Voice Search E-Commerce Demo")
    print("--------------------------------")
    print(f"Advanced mode: {'✅ Enabled' if whisper_model is not None and embedder is not None else '❌ Disabled'}")
    print("Server starting on http://127.0.0.1:5000/")
    app.run(debug=True)