# ASHA Connect: AI-Powered Healthcare Solution for Rural India

## Overview
ASHA Connect is an innovative healthcare solution designed to bridge the healthcare gap in rural India. By leveraging AI and voice-based technology, it empowers Accredited Social Health Activists (ASHAs) to provide better healthcare services to underserved communities.

## Problem Statement
Rural India faces significant healthcare challenges including:
- Limited access to qualified healthcare professionals
- Lack of diagnostic facilities
- Low health literacy
- Geographical barriers to healthcare access

ASHAs, while crucial to India's healthcare system, often lack adequate training and tools to effectively address complex health issues in their communities.

## Solution
ASHA Connect provides a comprehensive, voice-based AI assistant that:
1. Enables health assessments through natural conversation in local languages
2. Works offline in areas with limited connectivity
3. Provides decision support for common health conditions
4. Facilitates timely referrals to appropriate healthcare facilities
5. Supports continuous learning and skill development for ASHAs

## Key Features
- **Voice-Based Interaction**: Natural language processing in multiple Indian languages
- **Offline Capability**: Functions without continuous internet connectivity
- **AI-Powered Diagnostics**: Uses Llama 3 and other open-source AI models for health assessments
- **Secure Data Management**: Ensures patient privacy and data security
- **Continuous Learning**: Improves over time through feedback loops

## Technical Architecture

### Core Components
1. **Voice Interface Layer**
   - Speech-to-text and text-to-speech engines (via voice_service.py)
   - Natural language understanding modules
   - Support for multiple Indian languages (configured in .env)

2. **AI Processing Layer**
   - Health assessment logic (via health_service.py)
   - Decision support system
   - Llama 3 integration for advanced reasoning (via ai_models.py)

3. **Data Management Layer**
   - Secure patient data storage (via MongoDB)
   - Offline-first architecture (via offline_manager.py)
   - Synchronization protocols (via sync_service.py)

4. **Integration Layer**
   - Connectivity with healthcare systems (via API routes)
   - Telephony services for voice calls (via telephony.py)
   - User management and authentication (via user_service.py)

## Installation

### Prerequisites
- Python 3.8+
- MongoDB
- FFmpeg (for audio processing)
- PyTorch (for AI models)
- Internet connection for initial setup

### Setup Instructions
```bash
# Clone the repository
git clone https://github.com/Bharath-tars/ASHA_Connect.git
cd pragati

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the application
python app.py
```

## Project Structure
```
pragati/
├── app.py                  # Main application entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── services/               # Core business logic
│   ├── __init__.py         # Package initialization
│   ├── voice_service.py    # Voice processing service
│   ├── health_service.py   # Health assessment service
│   ├── user_service.py     # User management service
│   ├── sync_service.py     # Data synchronization service
│   ├── ai_models.py        # AI model integration
│   ├── offline_manager.py  # Offline functionality management
│   └── telephony.py        # Telephony services
├── data/                   # Data management
│   ├── __init__.py         # Package initialization
│   ├── database.py         # Database connection
│   ├── models.py           # Data models
│   └── repository.py       # Data access layer
├── api/                    # API endpoints
│   ├── __init__.py         # Package initialization
│   └── routes/             # API routes
│       ├── __init__.py     # Routes initialization
│       ├── admin_routes.py # Admin interface routes
│       ├── health_routes.py# Health assessment routes
│       ├── user_routes.py  # User management routes
│       └── voice_routes.py # Voice processing routes
```

## Usage
ASHA Connect is designed to be used by healthcare workers in the field. The application can be accessed through:

1. **Mobile Application**: Primary interface for ASHAs
2. **Web Interface**: For administrators and supervisors
3. **Voice Calls**: For areas with basic feature phones

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Contributing
Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more details.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements
- Ministry of Health and Family Welfare, Government of India
- National Health Mission
- ASHA workers across India who provided valuable feedback
- Open-source AI community

## Contact
For questions or support, please contact [Sudarsanam Bharath](mailto:bharath.sudarsanam04@gmail.com).
