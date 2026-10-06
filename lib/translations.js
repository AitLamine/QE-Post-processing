// Same pattern as CrystalEdu Lab's lib/translations.js: a flat EN/FR string
// dictionary for static UI chrome, plus separate FR override maps (keyed by
// category/module id) for the outline-derived content in lib/modules.js.
// lib/modules.js itself stays English-only and untouched — these are lookup
// overlays, not a rewrite of the data model.

export const STRINGS = {
  en: {
    intro1:
      "Upload raw calculation/reference files, pick a task, fill a short parameter form, and download a zip with the processed results — no terminal, no editing scripts.",
    intro2:
      "This covers post-processing and input generation only: no page here runs an actual DFT calculation. Every module below is a candidate page — most are interface previews for now, with real processing scripts adopted one module at a time.",
    footerNote: "post-processing / input-generation only — no DFT calculation runs here",
    breadcrumbAll: "All modules",
    sectionUpload: "1. Upload",
    sectionParameters: "2. Parameters",
    sectionProcess: "3. Process & download",
    submitButton: "Process & download zip",
    noticeCandidate:
      "This page previews the interface. The actual processing script isn't wired up yet — submitting will download a placeholder zip showing the expected output structure, not real results.",
    noticeReview:
      "Once implemented, this module's output will still need a human to sanity-check the result before treating it as final.",
    dropzoneText: "Drag and drop files here, or click to browse",
    removeButton: "remove",
    compareDefaultLabel: "Compare against (optional)",
    sampleLinkText: "Try it with sample data (coming soon)",
    sampleLinkTitle: "Sample files aren't published yet",
    noParamsNote: "No parameters needed beyond file selection.",
    errorMessage: "Something went wrong building the result zip. Please try again.",
    sizeLimitError: "Selected files exceed the {limit} limit for this slot.",
    jobIdle: "Idle",
    jobProcessing: "Processing...",
    jobDone: "Done",
    jobFailed: "Failed",
    themeToLight: "Switch to light theme",
    themeToDark: "Switch to dark theme",
    langToggle: "FR",
    modeUploadLabel: "Upload files (recommended)",
    modeManualLabel: "Enter data manually",
    manualEntryIntro:
      "Type or paste the raw content of each expected file below instead of uploading it. Nothing leaves your browser except the numbers you paste — use this if you'd rather not upload your actual calculation files or structure.",
    manualPdosAddButton: "+ Add another orbital/atom entry",
    manualPdosRemoveButton: "remove",
    manualDosForFermiLabel: "dos.x output (optional — paste it only to auto-detect the VBM/Fermi energy)",
    manualEntryRequiredNote: "Required in this mode.",
  },
  fr: {
    intro1:
      "Téléversez vos fichiers de calcul ou de référence, choisissez une tâche, remplissez un court formulaire de paramètres, et téléchargez une archive zip avec les résultats traités — pas de terminal, pas de script à modifier.",
    intro2:
      "Ceci couvre uniquement le post-traitement et la génération de fichiers d'entrée : aucune page ici n'exécute un vrai calcul DFT. Chaque module ci-dessous est une page candidate — la plupart sont pour l'instant des aperçus d'interface, les vrais scripts de traitement étant intégrés module par module.",
    footerNote: "post-traitement / génération de fichiers d'entrée uniquement — aucun calcul DFT ne s'exécute ici",
    breadcrumbAll: "Tous les modules",
    sectionUpload: "1. Téléversement",
    sectionParameters: "2. Paramètres",
    sectionProcess: "3. Traitement et téléchargement",
    submitButton: "Traiter et télécharger le zip",
    noticeCandidate:
      "Cette page présente un aperçu de l'interface. Le script de traitement réel n'est pas encore intégré — la soumission téléchargera une archive zip montrant la structure de sortie attendue, pas de vrais résultats.",
    noticeReview:
      "Une fois implémenté, le résultat de ce module devra encore être vérifié par une personne avant d'être considéré comme définitif.",
    dropzoneText: "Glissez-déposez des fichiers ici, ou cliquez pour parcourir",
    removeButton: "retirer",
    compareDefaultLabel: "Comparer avec (optionnel)",
    sampleLinkText: "Essayer avec des données d'exemple (bientôt disponible)",
    sampleLinkTitle: "Les fichiers d'exemple ne sont pas encore publiés",
    noParamsNote: "Aucun paramètre nécessaire au-delà du choix des fichiers.",
    errorMessage: "Une erreur s'est produite lors de la création du zip. Veuillez réessayer.",
    sizeLimitError: "Les fichiers sélectionnés dépassent la limite de {limit} pour cet emplacement.",
    jobIdle: "En attente",
    jobProcessing: "Traitement en cours...",
    jobDone: "Terminé",
    jobFailed: "Échec",
    themeToLight: "Passer au thème clair",
    themeToDark: "Passer au thème sombre",
    langToggle: "EN",
    modeUploadLabel: "Téléverser des fichiers (recommandé)",
    modeManualLabel: "Saisir les données manuellement",
    manualEntryIntro:
      "Tapez ou collez le contenu brut de chaque fichier attendu ci-dessous plutôt que de le téléverser. Rien ne quitte votre navigateur à part les chiffres que vous collez — utilisez ceci si vous préférez ne pas téléverser vos vrais fichiers de calcul ou votre structure.",
    manualPdosAddButton: "+ Ajouter une autre entrée orbitale/atome",
    manualPdosRemoveButton: "retirer",
    manualDosForFermiLabel: "Sortie dos.x (optionnel — à coller seulement pour détecter automatiquement l'énergie VBM/Fermi)",
    manualEntryRequiredNote: "Requis dans ce mode.",
  },
}

export const STATUS_LABELS_FR = {
  candidate: "Candidat",
  'script-ready': "Script prêt",
  'gui-adopted': "Interface adoptée",
  'standalone-ready': "Version autonome prête",
}

export const CATEGORY_FR = {
  'electronic-structure': { name: "Structure électronique" },
  'optical-dielectric': { name: "Propriétés optiques / diélectriques" },
  'charge-bonding': { name: "Analyse de charge / liaison" },
}

const EPS_MANUAL_ENTRY_LABELS_FR = {
  epsr: "Sortie epsilon.x, partie réelle (epsr) — collez son contenu",
  epsi: "Sortie epsilon.x, partie imaginaire (epsi) — collez son contenu",
}

export const MODULE_FR = {
  'band-dos-plotter': {
    title: "Traceur de structure de bandes + DOS",
    outputDescription: "Figure de structure de bandes et figure de DOS séparées (une image chacune), CSV des deux courbes.",
    inputFiles: ["Fichier de sortie .dat.gnu de bands.x", "Fichier de sortie dos.x"],
    paramLabels: {
      energyShift: "Énergie VBM/Fermi (eV) — optionnel, détectée automatiquement depuis l'en-tête du fichier dos.x si laissé vide",
      kPathTicks: "Points de haute symétrie sous forme de paires position:étiquette (ex. 0:Γ,0.577:M,0.911:K) — optionnel, selon votre propre chemin k",
      occupiedSplit: "Séparation occupé / inoccupé",
      figureFormat: "Format de figure",
      xRange: "Plage de l'axe X (optionnel — auto si laissé vide)",
      yRange: "Plage de l'axe Y (optionnel — auto si laissé vide)",
    },
    paramOptions: {
      occupiedSplit: {
        'Show both': "Afficher les deux",
        'Occupied only': "Occupé seulement",
        'Unoccupied only': "Inoccupé seulement",
      },
      figureFormat: { PNG: "PNG", 'LaTeX (pgfplots)': "LaTeX (pgfplots)", Both: "Les deux" },
    },
    manualEntryLabels: {
      bandsGnu: "Sortie .dat.gnu de bands.x — collez son contenu",
      dos: "Sortie de dos.x — collez son contenu (gardez la ligne d'en-tête EFermi si présente)",
    },
  },
  'pdos-plotter': {
    title: "Traceur de DOS projetée (pDOS)",
    outputDescription: "Une figure par espèce (pas empilées dans un seul panneau), CSV combiné.",
    inputFiles: ["Fichiers de sortie projwfc.x pdos_atm (un par orbitale/atome) — à étiqueter après téléversement"],
    paramLabels: {
      energyShift: "Énergie VBM/Fermi (eV) — optionnel si vous téléversez aussi le fichier dos.x ci-dessous, sinon requis",
      figureFormat: "Format de figure",
      xRange: "Plage de l'axe X (optionnel — auto si laissé vide)",
      yRange: "Plage de l'axe Y (optionnel — auto si laissé vide)",
    },
    paramOptions: {
      figureFormat: { PNG: "PNG", 'LaTeX (pgfplots)': "LaTeX (pgfplots)", Both: "Les deux" },
    },
  },
  'effective-mass-extractor': {
    title: "Extracteur de masse effective",
    outputDescription:
      "Tableau de masse (par direction/type de porteur), graphique de qualité de l'ajustement.",
    inputFiles: ["Fichier(s) de structure de bandes selon une ou plusieurs directions k"],
    paramLabels: {
      kDirection: "Direction(s) k (séparées par des virgules)",
      bandIndex: "Indice de bande",
      fitWindow: "Fenêtre d'ajustement parabolique (plage k)",
      figureFormat: "Format de figure",
      xRange: "Plage de l'axe X (optionnel — auto si laissé vide)",
      yRange: "Plage de l'axe Y (optionnel — auto si laissé vide)",
    },
    paramOptions: {
      figureFormat: { PNG: "PNG", 'LaTeX (pgfplots)': "LaTeX (pgfplots)", Both: "Les deux" },
    },
  },
  'dielectric-function-plotter': {
    title: "Traceur de fonction diélectrique",
    outputDescription: "Figures séparées ε1(ω) et ε2(ω) (une image chacune).",
    inputFiles: [
      "Sortie de type epsilon.x, partie réelle",
      "Sortie de type epsilon.x, partie imaginaire",
    ],
    paramLabels: {
      polarization: "Direction de polarisation",
      xAxis: "Grandeur de l'axe X",
      figureFormat: "Format de figure",
      xRange: "Plage de l'axe X (optionnel — auto si laissé vide ; 100,1000 par défaut pour la longueur d'onde)",
      yRange: "Plage de l'axe Y (optionnel — auto si laissé vide)",
    },
    paramOptions: {
      polarization: { Ordinary: "Ordinaire", Extraordinary: "Extraordinaire" },
      xAxis: { 'Energy (eV)': "Énergie (eV)", 'Wavelength (nm)': "Longueur d'onde (nm)" },
      figureFormat: { PNG: "PNG", 'LaTeX (pgfplots)': "LaTeX (pgfplots)", Both: "Les deux" },
    },
    manualEntryLabels: EPS_MANUAL_ENTRY_LABELS_FR,
  },
  'optical-magnitudes-plotter': {
    title: "Traceur de grandeurs optiques",
    outputDescription: "Une figure par grandeur sélectionnée, plus un CSV combiné.",
    inputFiles: ["Sortie de type epsilon.x, partie réelle/imaginaire"],
    paramLabels: {
      magnitudes: "Grandeur(s) à tracer",
      xAxis: "Grandeur de l'axe X",
      figureFormat: "Format de figure",
      xRange: "Plage de l'axe X (optionnel — auto si laissé vide ; 100,1000 par défaut pour la longueur d'onde)",
      yRange: "Plage de l'axe Y (optionnel — auto si laissé vide)",
    },
    paramOptions: {
      magnitudes: {
        'Refractive index': "Indice de réfraction",
        'Extinction coefficient': "Coefficient d'extinction",
        'Reflectivity': "Réflectivité",
        'Absorption coefficient': "Coefficient d'absorption",
        'Energy-loss function': "Fonction de perte d'énergie",
        'Optical conductivity': "Conductivité optique",
      },
      xAxis: { 'Energy (eV)': "Énergie (eV)", 'Wavelength (nm)': "Longueur d'onde (nm)" },
      figureFormat: { PNG: "PNG", 'LaTeX (pgfplots)': "LaTeX (pgfplots)", Both: "Les deux" },
    },
    manualEntryLabels: EPS_MANUAL_ENTRY_LABELS_FR,
  },
  'tauc-plot-extractor': {
    title: "Extracteur de tracé de Tauc / bande interdite",
    outputDescription:
      "Tracé de Tauc avec la valeur de bande interdite ajustée indiquée, valeur et résumé de la fenêtre d'ajustement.",
    inputFiles: [
      "Sortie de type epsilon.x, partie réelle",
      "Sortie de type epsilon.x, partie imaginaire",
    ],
    paramLabels: {
      transitionType: "Type de transition",
      fitWindow: "Fenêtre d'ajustement (plage d'énergie, optionnel — détectée automatiquement si laissée vide)",
      electronicGap: "Bande interdite électronique DFT propre au matériau, en eV (optionnel, mais recommandé — ancre la recherche automatique pour éviter qu'elle ne se verrouille sur la mauvaise caractéristique d'absorption)",
      figureFormat: "Format de figure",
      xRange: "Plage de l'axe X (optionnel — auto si laissé vide)",
      yRange: "Plage de l'axe Y (optionnel — auto si laissé vide)",
    },
    paramOptions: {
      transitionType: { Direct: "Directe", Indirect: "Indirecte" },
      figureFormat: { PNG: "PNG", 'LaTeX (pgfplots)': "LaTeX (pgfplots)", Both: "Les deux" },
    },
    manualEntryLabels: EPS_MANUAL_ENTRY_LABELS_FR,
  },
  'bader-charge-analyzer': {
    title: "Analyseur de charges de Bader",
    outputDescription:
      "Tableau par atome : charge de Bader, charge nette, ionicité (%) et covalence (%) ; résumé par espèce.",
    inputFiles: ["ACF.dat (du code bader)"],
    paramLabels: {
      elementOrder: "Élément par atome, dans l'ordre d'ACF.dat (séparés par des virgules, ex. Zn,Zn,O,O)",
      valenceElectrons: "Électrons de valence par espèce, selon votre pseudopotentiel (ex. Zn:20,O:6)",
      formalCharges: "Charge ionique formelle par espèce (ex. Zn:2,O:-2) — pour le ratio ionicité/covalence",
    },
    manualEntryLabels: {
      acf: "Contenu d'ACF.dat (du code bader) — collez son contenu",
    },
  },
}

export function categoryName(category, lang) {
  return (lang === 'fr' && CATEGORY_FR[category.id]?.name) || category.name
}

export function categoryDescription(category, lang) {
  return (lang === 'fr' && CATEGORY_FR[category.id]?.description) || category.description
}

export function moduleTitle(module, lang) {
  return (lang === 'fr' && MODULE_FR[module.id]?.title) || module.title
}

export function moduleOutputDescription(module, lang) {
  return (lang === 'fr' && MODULE_FR[module.id]?.outputDescription) || module.outputDescription
}

export function moduleInputFiles(module, lang) {
  const fr = MODULE_FR[module.id]?.inputFiles
  return (lang === 'fr' && fr) || module.inputFiles
}

export function moduleCompareLabel(module, lang) {
  const fr = MODULE_FR[module.id]?.compareLabel
  return (lang === 'fr' && fr) || module.compareLabel
}

export function paramLabel(module, param, lang) {
  const fr = MODULE_FR[module.id]?.paramLabels?.[param.id]
  return (lang === 'fr' && fr) || param.label
}

export function paramOptionLabel(module, param, opt, lang) {
  const fr = MODULE_FR[module.id]?.paramOptions?.[param.id]?.[opt]
  return (lang === 'fr' && fr) || opt
}

export function manualEntryLabel(module, fileKey, fallbackLabel, lang) {
  const fr = MODULE_FR[module.id]?.manualEntryLabels?.[fileKey]
  return (lang === 'fr' && fr) || fallbackLabel
}
