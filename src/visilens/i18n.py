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
ROWS.update({
"❤️ Support me": ("❤️ Support me","❤️ Unterstütze mich","❤️ Soutenez-moi"),
"✦ Auto-Select": ("✦ Auto-Select","✦ Auto-Select","✦ Auto-Select"),
"Auto-Select": ("Auto-Select","Auto-Select","Auto-Select"),
"⚙ Criteri": ("⚙ Criteria","⚙ Kriterien","⚙ Critères"),
"Criteri Auto-Select": ("Auto-Select criteria","Auto-Select-Kriterien","Critères Auto-Select"),
"Quale copia vuoi conservare?": ("Which copy should be kept?","Welche Kopie soll behalten werden?","Quelle copie conserver ?"),
"Preferisci la risoluzione maggiore": ("Prefer higher resolution","Höhere Auflösung bevorzugen","Privilégier la meilleure résolution"),
"A parità, preferisci il file più grande": ("If tied, prefer larger files","Bei Gleichstand größere Datei bevorzugen","À égalité, privilégier le fichier le plus volumineux"),
"La dimensione del file non garantisce qualità migliore.": ("File size does not guarantee higher quality.","Dateigröße garantiert keine höhere Qualität.","La taille du fichier ne garantit pas une meilleure qualité."),
"Cartelle protette": ("Protected folders","Geschützte Ordner","Dossiers protégés"),
"Aggiungi": ("Add","Hinzufügen","Ajouter"),
"Rimuovi": ("Remove","Entfernen","Supprimer"),
"Cestino": ("Recycle Bin","Papierkorb","Corbeille"),
"Scansione in corso…": ("Scanning…","Scan läuft…","Analyse en cours…"),
"Arresto dopo l'immagine corrente…": ("Stopping after current image…","Stopp nach aktuellem Bild…","Arrêt après l'image en cours…"),
"Seleziona almeno una cartella.": ("Select at least one folder.","Bitte mindestens einen Ordner auswählen.","Sélectionnez au moins un dossier."),
"Scansione non riuscita": ("Scan failed","Scan fehlgeschlagen","Échec de l’analyse"),
"Errore durante la scansione": ("Error during scan","Fehler beim Scannen","Erreur pendant l’analyse"),
"File ignorati": ("Files skipped","Übersprungene Dateien","Fichiers ignorés"),
"Conferma chiusura": ("Confirm exit","Beenden bestätigen","Confirmer la fermeture"),
"Vuoi davvero chiudere VisiLens?": ("Are you sure you want to close VisiLens?","VisiLens wirklich schließen?","Voulez-vous vraiment fermer VisiLens ?"),
"I gruppi trovati e le selezioni correnti non saranno più disponibili alla prossima apertura. Nessuna immagine verrà eliminata.": ("Current groups and selections will not be available next time. No images will be deleted.","Aktuelle Gruppen und Auswahlen sind beim nächsten Start nicht verfügbar. Es werden keine Bilder gelöscht.","Les groupes et sélections actuels ne seront plus disponibles au prochain démarrage. Aucune image ne sera supprimée."),
"Attendi il completamento dell'elaborazione prima di chiudere.": ("Wait until processing finishes before closing.","Bitte warten Sie bis die Verarbeitung beendet ist.","Attendez la fin du traitement avant de fermer."),
"Chiudi": ("Close","Schließen","Fermer"),
"Annulla": ("Cancel","Abbrechen","Annuler"),
"Nessuna selezione": ("No selection","Keine Auswahl","Aucune sélection"),
"Seleziona prima le immagini.": ("Select images first.","Wählen Sie zuerst Bilder aus.","Sélectionnez d'abord les images."),
"Conserva un'immagine": ("Keep an image","Bild behalten","Conserver une image"),
"Conferma cestino": ("Confirm Recycle Bin","Papierkorb bestätigen","Confirmer la mise à la corbeille"),
"Anteprima non disponibile": ("Preview unavailable","Vorschau nicht verfügbar","Aperçu indisponible"),
"Selezione annullata; nessun file modificato": ("Selection cleared; no files changed","Auswahl aufgehoben; keine Dateien geändert","Sélection annulée ; aucun fichier modifié"),
"Criteri salvati. Premi Auto-Select per applicarli.": ("Criteria saved. Use Auto-Select to apply them.","Kriterien gespeichert. Mit Auto-Select anwenden.","Critères enregistrés. Utilisez Auto-Select pour les appliquer."),
})

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
