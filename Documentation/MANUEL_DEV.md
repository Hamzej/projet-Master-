Smart Attendance System – Guide Développeur
🏗️ Architecture générale
Le système est composé de trois couches principales :

Core Python (Reconnaissance faciale)

face_processor.py → détection, alignement, embeddings (ArcFace).

enrollment.py → enrôlement étudiants (image, webcam, bulk).

attendance.py → reconnaissance temps réel et journalisation.

database.py → gestion SQLite (étudiants, embeddings, présences).

Backend Django (API REST)

models.py → tables SQL (Student, Embedding, Attendance).

serializers.py → conversion objets ↔ JSON.

views.py → API REST (enrôlement, reconnaissance, stats).

urls.py → routes API.

tests.py → tests unitaires Django.

Frontend React (Interface Web)

App.js → point d’entrée interface.

EnrollmentForm.js → formulaire enrôlement.

AttendanceDashboard.js → tableau de suivi.

CameraCapture.js → capture webcam.

api.js → communication avec Django REST.

⚙️ Workflow technique
1. Enrôlement
L’utilisateur envoie une photo (webcam ou fichier).

Python → ArcFace génère un embedding (512-dim).

Django API → stocke embedding + photo + métriques qualité.

React → formulaire d’enrôlement (EnrollmentForm.js).

2. Reconnaissance
Python → extrait embedding du flux vidéo.

Django API → compare avec embeddings stockés (cosine similarity).

React → composant CameraCapture.js affiche résultat (étudiant reconnu ou inconnu).

3. Présence
Django API → enregistre présence avec timestamp + confiance.

React → AttendanceDashboard.js affiche journal et statistiques.

🔗 API REST (Django)
Endpoints principaux
POST /api/students/ → créer étudiant.

POST /api/students/{id}/enroll/ → enrôler avec embedding.

POST /api/attendance/recognize/ → reconnaissance faciale.

GET /api/attendance/stats/ → statistiques globales.

GET /api/attendance/ → journal des présences.

🎨 Frontend React
Navigation
Dashboard → statistiques + journal.

Enroll Student → formulaire enrôlement.

Camera Capture → capture webcam + reconnaissance.

Communication
api.js → instance axios pointant vers http://localhost:8000/api.

Chaque composant utilise api.get / api.post pour interagir avec Django.

🧪 Tests
Python
test_system.py → tests unitaires pour FaceProcessor, Database, ImageQuality, intégration.

Django
tests.py → tests unitaires pour modèles et API REST.

📈 Performances
CPU : 5–10 FPS.

GPU : 30–60 FPS.

Accuracy (FERET) : AUC 0.99, Rank-1 > 99%.

🔮 Extensions possibles
Interface web avancée (Django + React).

Notifications email/SMS.

Exportation des présences (CSV, Excel).

Application mobile (React Native).