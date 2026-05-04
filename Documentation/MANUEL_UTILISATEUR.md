Smart Attendance System – Guide Utilisateur
📥 Installation
Installer Python 3.8+  
Vérifie avec :

bash
python --version
Installer les dépendances

bash
pip install -r requirements.txt
(Optionnel) Installer CUDA pour GPU

NVIDIA CUDA Toolkit 11.8+

cuDNN 8.6+

🚀 Démarrage rapide
Lancer le menu interactif :

bash
python main.py
Options disponibles :

Enrôler un étudiant depuis une image

Enrôler un étudiant via webcam

Enrôlement en masse depuis un dossier

Détection en temps réel (présences)

Statistiques de la base de données

Consulter les présences

Quitter

📸 Enrôlement des étudiants
Depuis la webcam
Choisir l’option 2 dans le menu.

Regarder la caméra, attendre un score de qualité ≥ 70%.

Appuyer sur ESPACE pour capturer, ESC pour annuler.

La photo est sauvegardée dans enrolled_students/.

L’étudiant est ajouté à la base avec un ID unique.

Enrôlement en masse
Préparer un dossier :

Code
student_photos/
├── Ahmed Al-Mansouri/photo.jpg
├── Fatima Al-Zahra/enrollment.jpg
└── Muhammad Hassan/face.png
Choisir l’option 3 et entrer le chemin du dossier.

🎥 Détection en temps réel
Choisir l’option 4.

Contrôles :

R → recharger la base

S → afficher statistiques

Q ou ESC → quitter

Affichage :

✅ Vert → étudiant reconnu, présence enregistrée

❌ Rouge → personne inconnue

📊 Consultation des présences
Option 5 → statistiques globales (étudiants actifs, embeddings, présences du jour).

Option 6 → journal des présences du jour ou statistiques par étudiant (30 jours).

⚙️ Configuration
Modifier config.py :

python
SIMILARITY_THRESHOLD = 0.35  # 0.25 strict, 0.45 permissif
CAMERA_INDEX = 0             # changer si plusieurs caméras
GPU_CONTEXT = 0              # 0=GPU, -1=CPU
ENROLLMENT_QUALITY_THRESHOLD = 0.7
🐛 Dépannage
Caméra non détectée : tester indices 0,1,2…

Précision faible :

meilleures photos d’enrôlement (lumière, visage centré)

ajuster le seuil de similarité

enrôler plusieurs photos par étudiant

Erreur base de données : supprimer fichiers students.db-shm et students.db-wal.

Erreur CUDA : forcer CPU avec ctx_id=-1.

📈 Performances
CPU : 5–10 FPS

GPU : 30–60 FPS

Accuracy (FERET) : AUC 0.99, Rank-1 > 99%

📚 Références
ArcFace : arxiv.org/abs/1801.07698

InsightFace : github.com/deepinsight/insightface (github.com in Bing)

OpenCV : docs.opencv.org

👨‍💻 Auteur
Projet Master – Smart Attendance System
Université : [Ton Université]
Date : 2026