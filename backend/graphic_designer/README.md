# Real Estate AI Graphic Designer SaaS

A production-ready AI-powered graphic design automation system for real estate marketing with self-training capabilities.

## 🚀 Features

### Core Design Engine
- **AI-Powered Design Generation**: Generate professional real estate marketing creatives from text descriptions
- **Multi-Gen Ensemble**: Generate N variations and automatically select the best one
- **Smart Composition**: Dynamic layout with text overlay, gradients, and brand elements
- **Platform Optimization**: Tailored designs for Instagram, Facebook, Website, Print, etc.

### Self-Training Pipeline
- **Auto Dataset Capture**: Every generation is automatically saved with metadata
- **AI Evaluation**: Designs scored on photorealism, layout, readability, and relevance
- **Active Learning**: Intelligent sample selection for optimal training
- **LoRA Fine-Tuning**: Vertex AI integration for model customization
- **Example Learning**: Upload reference designs for the AI to learn from

### Multi-Tenant SaaS
- **API Key Authentication**: Secure tenant isolation
- **Brand Kits**: Custom colors, logos, and typography per tenant
- **Usage Quotas**: Track and limit API usage
- **Asset Libraries**: Store generated designs per tenant

### Quality Assurance
- **Layout Validator**: Aspect ratio, contrast, padding checks
- **Error Clustering**: Identify common failure patterns
- **Feedback Loop**: User ratings improve future generations

## 📁 Project Structure

```
backend/graphic_designer/
├── main.py              # Legacy endpoint (backward compatible)
├── main_v2.py           # New SaaS entry point
├── requirements.txt     # Python dependencies
├── .env                 # Environment configuration
│
├── app/
│   ├── models/
│   │   ├── schemas.py   # Pydantic data models
│   │   └── database.py  # JSON-based data layer
│   │
│   ├── routes/
│   │   ├── design_routes.py     # Design generation endpoints
│   │   ├── feedback_routes.py   # User feedback endpoints
│   │   ├── training_routes.py   # Model training endpoints
│   │   ├── tenant_routes.py     # Tenant management
│   │   └── example_routes.py    # Example upload endpoints
│   │
│   ├── services/
│   │   └── design_service.py    # Core design orchestration
│   │
│   ├── evaluators/
│   │   └── evaluator.py         # Gemini Vision scoring
│   │
│   ├── validators/
│   │   └── validator.py         # Layout quality checks
│   │
│   ├── trainers/
│   │   └── train_lora.py        # Vertex AI LoRA training
│   │
│   ├── datasets/
│   │   └── active_selector.py   # Active learning sampler
│   │
│   ├── storage/
│   │   └── storage_service.py   # GCS/local file storage
│   │
│   ├── tenant/
│   │   └── tenant_service.py    # Multi-tenant logic
│   │
│   └── brand/
│       └── brand_service.py     # Brand kit management
│
├── dataset/
│   ├── images/          # Generated images
│   └── metadata.jsonl   # Training metadata
│
└── data/
    ├── tenants.json     # Tenant registry
    ├── brand_kits.json  # Brand configurations
    └── model_registry.json  # Trained model versions
```

## 🔧 Installation

```bash
cd backend/graphic_designer
pip install -r requirements.txt
```

## ⚙️ Configuration

Create a `.env` file:

```bash
# Required
GOOGLE_CLOUD_PROJECT=your-project-id
GEMINI_API_KEY=your-gemini-api-key

# Optional
GOOGLE_CLOUD_LOCATION=us-central1
GCS_TRAINING_BUCKET=your-training-bucket
PORT=8003
```

## 🚀 Running the Server

### Development
```bash
python main_v2.py
```

### Production
```bash
uvicorn main_v2:app --host 0.0.0.0 --port 8003
```

## 📚 API Endpoints

### Design Generation

#### Generate Single Design
```http
POST /api/v2/design/generate
Content-Type: application/json

{
    "raw_input": "3 BHK luxury apartment in Baner, river view, ₹2Cr",
    "category": "luxury",
    "platform": "Instagram Story",
    "style": "modern",
    "aspectRatio": "9:16"
}
```

#### Generate Ensemble (Best of N)
```http
POST /api/v2/design/generate-ensemble?num_variations=3
Content-Type: application/json

{
    "raw_input": "Premium villa with pool",
    "category": "luxury"
}
```

### Feedback

#### Submit Feedback
```http
POST /api/v2/feedback/
Content-Type: application/json

{
    "design_id": "uuid-here",
    "feedback_type": "approve",
    "rating": 5,
    "comments": "Great quality!"
}
```

### Training

#### Start Training Job
```http
POST /api/v2/training/train-model
Content-Type: application/json

{
    "model_type": "imagen",
    "epochs": 100
}
```

#### Check Training Status
```http
GET /api/v2/training/training-status/{job_id}
```

#### List Models
```http
GET /api/v2/training/models
```

### Tenant Management

#### Register Tenant
```http
POST /api/v2/tenants/register
Content-Type: application/json

{
    "name": "Acme Realty",
    "email": "admin@acme.com"
}
```

Response includes API key for future requests.

#### Create Brand Kit
```http
POST /api/v2/tenants/brand-kits
X-API-Key: sk_xxxxxxxxxxxxx
Content-Type: application/json

{
    "name": "Acme Brand",
    "primary_color": "#1a1a2e",
    "accent_color": "#e94560"
}
```

### Example Upload

#### Upload Design Example
```http
POST /api/v2/examples/upload
Content-Type: multipart/form-data

file: [flyer.png]
category: luxury
style: modern
```

## 🔄 Training Pipeline

1. **Generate Designs**: Use `/api/v2/design/generate` to create designs
2. **Auto-Capture**: All generations are saved with metadata
3. **Feedback**: Users rate designs via `/api/v2/feedback/`
4. **Selection**: Active learning selects optimal training samples
5. **Training**: Call `/api/v2/training/train-model` to fine-tune
6. **Deployment**: Activate new model via `/api/v2/training/models/{id}/activate`

## 📊 Evaluation Metrics

Each design is scored (0-10) on:
- **Photorealism**: Image quality and realism
- **Layout Alignment**: Proper text and element positioning
- **Readability**: Text contrast and legibility
- **Real Estate Relevance**: Professional marketing appearance
- **Overall Quality**: Combined assessment

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────┐
│   Next.js UI    │────▶│   FastAPI SaaS   │────▶│  Vertex AI     │
│   (Frontend)    │     │   (Backend)      │     │  (Imagen/Gemini)│
└─────────────────┘     └──────────────────┘     └────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   GCS Storage    │
                        │   (Datasets)     │
                        └──────────────────┘
```

## 🔐 Authentication

Endpoints support optional API key authentication:

```http
X-API-Key: sk_xxxxxxxxxxxxx
```

Authenticated requests:
- Track usage per tenant
- Apply brand kits
- Access tenant-specific data

## 📈 Dataset Statistics

```http
GET /api/v2/training/dataset/stats
```

Returns:
- Total samples
- Approved/rejected counts
- Average scores
- Category/platform/style distributions

## 🧠 Active Learning

The system automatically prioritizes training samples based on:
1. Low AI scores (model struggles → needs training)
2. Low-frequency categories (underrepresented data)
3. User-approved designs (confirmed quality)

```http
GET /api/v2/training/dataset/balance
```

## 📝 License

Private / Commercial

## 🤝 Support

For issues or feature requests, contact the development team.
