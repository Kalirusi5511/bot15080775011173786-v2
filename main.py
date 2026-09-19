# main.py
import os
import staypresent

# ---- 1. Minimaler HTTP-Server für Render Health-Check ----
# Render erwartet einen HTTP-Port, sonst wird der Dienst als "unhealthy" markiert.
# staypresent.web.json() startet einen winzigen HTTP-Server,
# der auf alle Anfragen mit {"status": "running"} antwortet.
staypresent.web.json({"status": "running"})

# ---- 2. Deinen bestehenden Bot als Unterprozess starten ----
# staypresent.run() führt app.py aus und hält die Verbindung aufrecht.
# Der Port wird automatisch aus der Umgebungsvariable PORT gelesen.
staypresent.run("app.py", port=int(os.getenv("PORT", 8080)))
