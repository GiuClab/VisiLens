"""VisiLens translations. Italian is the source language; English is default."""
LANGUAGES = {"en": "English", "it": "Italiano", "de": "Deutsch", "fr": "Français"}
_active = "en"
# Italian: English, German, French
ROWS = {
"File": ("File","Datei","Fichier"),
"Modifica": ("Edit","Bearbeiten","Édition"),
"Opzioni": ("Options","Optionen","Options"),
"Aiuto": ("Help","Hilfe","Aide"),
"Lingua": ("Language","Sprache","Langue"),
"Tema": ("Theme","Design","Thème"),
"Chiaro": ("Light","Hell","Clair"),
"Scuro": ("Dark","Dunkel","Sombre"),
"Segui Windows": ("Follow Windows","Windows-Einstellung","Suivre Windows"),
"Aggiungi cartella…": ("Add folder…","Ordner hinzufügen…","Ajouter un dossier…"),
"Avvia scansione": ("Start scan","Scan starten","Lancer l’analyse"),
"Interrompi": ("Stop","Stopp","Arrêter"),
"Esci": ("Exit","Beenden","Quitter"),
"Annulla selezione": ("Clear selection","Auswahl aufheben","Effacer la sélection"),
"⚙ Criteri": ("⚙ Criteria","⚙ Kriterien","⚙ Critères"),
"Criteri Auto-Select": ("Auto-Select criteria","Auto-Select-Kriterien","Critères Auto-Select"),
"Includi file e cartelle nascosti": ("Include hidden files and folders","Versteckte Dateien und Ordner einbeziehen","Inclure les fichiers et dossiers cachés"),
"Informazioni su VisiLens": ("About VisiLens","Über VisiLens","À propos de VisiLens"),
"Progetto su GitHub": ("Project on GitHub","Projekt auf GitHub","Projet sur GitHub"),
"Seleziona le cartelle da analizzare": ("Choose folders to scan","Ordner zum Scannen auswählen","Choisir les dossiers à analyser"),
"Cartelle selezionate": ("Selected folders","Ausgewählte Ordner","Dossiers sélectionnés"),
"Rimuovi cartella": ("Remove folder","Ordner entfernen","Supprimer le dossier"),
"Livello di somiglianza": ("Similarity level","Ähnlichkeitsstufe","Niveau de similarité"),
"Loose — confronto flessibile": ("Loose — flexible matching","Loose — großzügiger Vergleich","Loose — comparaison souple"),
"Basic — somiglianza equilibrata": ("Basic — balanced matching","Basic — ausgewogener Vergleich","Basic — comparaison équilibrée"),
"Strict — confronto rigoroso": ("Strict — precise matching","Strict — strenger Vergleich","Strict — comparaison stricte"),
"▶ Avvia scansione": ("▶ Start scan","▶ Scan starten","▶ Lancer l’analyse"),
"Immagini analizzate": ("Images scanned","Bilder analysiert","Images analysées"),
"Duplicati trovati": ("Duplicates found","Duplikate gefunden","Doublons trouvés"),
"Spazio recuperabile": ("Recoverable space","Freigebbarer Speicher","Espace récupérable"),
"Nessun file selezionato": ("No files selected","Keine Dateien ausgewählt","Aucun fichier sélectionné"),
"Anteprima": ("Preview","Vorschau","Aperçu"),
"Seleziona una miniatura": ("Select a thumbnail","Miniaturbild auswählen","Sélectionnez une miniature"),
"Nessuna immagine selezionata": ("No image selected","Kein Bild ausgewählt","Aucune image sélectionnée"),
"♲ Sposta selezionate nel cestino": ("♲ Move selected to Recycle Bin","♲ Auswahl in den Papierkorb","♲ Mettre la sélection à la corbeille"),
"Seleziona una cartella e avvia la scansione.": ("Choose a folder and start scanning.","Ordner auswählen und Scan starten.","Choisissez un dossier et lancez l’analyse."),
"Seleziona cartella": ("Choose folder","Ordner auswählen","Choisir un dossier"),
"Questo PC": ("This PC","Dieser PC","Ce PC"),
"Documenti": ("Documents","Dokumente","Documents"),
"Immagini": ("Pictures","Bilder","Images"),
"Musica": ("Music","Musik","Musique"),
"Video": ("Videos","Videos","Vidéos"),
"Oggetti 3D": ("3D Objects","3D-Objekte","Objets 3D"),
"Cestino": ("Recycle Bin","Papierkorb","Corbeille"),
"Anteprima…": ("Preview…","Vorschau…","Aperçu…"),
"Anteprima non disponibile": ("Preview unavailable","Vorschau nicht verfügbar","Aperçu indisponible"),
"Da conservare": ("Keep","Behalten","Conserver"),
"Selezionata per il cestino": ("Marked for Recycle Bin","Für Papierkorb markiert","Marquée pour la corbeille"),
"Conferma chiusura": ("Confirm exit","Beenden bestätigen","Confirmer la fermeture"),
"Vuoi davvero chiudere VisiLens?": ("Are you sure you want to close VisiLens?","VisiLens wirklich beenden?","Voulez-vous vraiment fermer VisiLens ?"),
"Chiudi": ("Close","Schließen","Fermer"),
"Annulla": ("Cancel","Abbrechen","Annuler"),
"Scansione in corso": ("Scan running","Scan läuft","Analyse en cours"),
"Nessuna selezione": ("No selection","Keine Auswahl","Aucune sélection"),
"Conferma cestino": ("Confirm Recycle Bin","Papierkorb bestätigen","Confirmer la mise à la corbeille"),
"Support me": ("Support me","Unterstütze mich","Soutenez-moi"),
}
def set_language(language: str) -> None:
    global _active
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    _active = language

def get_language() -> str:
    return _active

def tr(text: str) -> str:
    if _active == "it":
        return text
    row = ROWS.get(text)
    return row[("en", "de", "fr").index(_active)] if row else text
