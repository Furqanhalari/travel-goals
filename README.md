# ✈️ Travel Goals - Full Stack Travel Management System

**Travel Goals** is a premium, AI-powered travel platform designed to connect travelers with curated vacation packages. The project features a robust vendor management system, a responsive UI/UX, and an intelligent travel assistant.

## 🌟 Key Features

### 🤖 AI Travel Assistant
Integrates the **Groq API** (Llama 3) to provide real-time travel advice, destination descriptions, and package recommendations based on user preferences.

### 📱 Fully Responsive Design
Optimized for all devices. Custom CSS layouts ensure that destination cards, booking forms, and navigation menus are seamless on Desktop, Tablet, and Mobile.

### 🏢 Vendor Management
A dedicated workflow for travel vendors to submit new destinations and packages for admin approval, including a dashboard to track submission status.

### 🔒 Secure Authentication
Role-based access control (RBAC) for Admins, Vendors, and Customers, featuring hashed password security.

---

## 🛠️ Tech Stack

- **Frontend**: HTML5, CSS3 (Vanilla), JavaScript (ES6+)
- **Backend**: Flask (Python)
- **Database**: Oracle Database (via `cx_Oracle`)
- **AI**: Groq API (Llama 3.3 70b)
- **Environment**: Python-Dotenv for secure configuration

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Oracle Instant Client
- Groq API Key

### Installation

1. **Clone the repo**
   ```bash
   git clone https://github.com/Furqanhalari/travel-goals.git
   cd travel-goals
   ```

2. **Setup virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   DB_USER=your_oracle_user
   DB_PASSWORD=your_oracle_password
   DB_DSN=localhost:1521/XE
   GROQ_API_KEY=your_groq_key
   SECRET_KEY=your_flask_secret
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```

---

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.

## 👥 Contributors
- **Furqan Halari** - Initial Work
