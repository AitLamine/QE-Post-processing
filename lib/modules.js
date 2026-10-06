// Single source of truth for every candidate page, mirroring
// Post-Processing-WebApp-Outline.md. Add/edit modules here; the landing
// page and /task/[id] route are generated entirely from this data.
//
// Parameter field types understood by <ParameterForm>: text, number, select,
// multiselect, checkbox.

// Shared by every epsilon.x-based module (dielectric function, optical magnitudes, Tauc):
// the fixed-filename "epsr"/"epsi" keyword each needs to pass the backend's fail-closed
// role check (scripts/common/file_validation.py) when no real upload exists to carry it.
const EPS_MANUAL_ENTRY_FILES = [
  {
    key: 'epsr',
    filename: 'epsr_manual.dat',
    label: 'epsilon.x real-part (epsr) output — paste its content',
    placeholder:
      '# E(eV)   eps1_x    eps1_y    eps1_z\n0.000    5.1230    5.1230    4.9870\n' +
      '0.050    5.1300    5.1300    4.9900\n...',
  },
  {
    key: 'epsi',
    filename: 'epsi_manual.dat',
    label: 'epsilon.x imaginary-part (epsi) output — paste its content',
    placeholder:
      '# E(eV)   eps2_x    eps2_y    eps2_z\n0.000    0.0010    0.0010    0.0005\n' +
      '0.050    0.0020    0.0020    0.0012\n...',
  },
]

export const CATEGORIES = [
  {
    id: 'electronic-structure',
    name: 'Electronic structure',
    modules: [
      {
        id: 'band-dos-plotter',
        title: 'Band structure + DOS plotter',
        inputFiles: ['bands.x .dat.gnu output file', 'dos.x output file'],
        parameters: [
          { id: 'energyShift', label: 'VBM/Fermi energy (eV) — optional, auto-detected from the dos.x file header if left blank', type: 'text', default: '' },
          { id: 'kPathTicks', label: "High-symmetry k-points as position:label pairs (e.g. 0:Γ,0.577:M,0.911:K) — optional, from your own k-path setup", type: 'text', default: '' },
          {
            id: 'occupiedSplit',
            label: 'Occupied / unoccupied split',
            type: 'select',
            options: ['Show both', 'Occupied only', 'Unoccupied only'],
            default: 'Show both',
          },
          {
            id: 'figureFormat',
            label: 'Figure format',
            type: 'select',
            options: ['PNG', 'LaTeX (pgfplots)', 'Both'],
            default: 'PNG',
          },
          { id: 'xRange', label: 'X-axis range (optional — auto if left blank)', type: 'text', default: '' },
          { id: 'yRange', label: 'Y-axis (energy) range (optional — auto if left blank)', type: 'text', default: '' },
        ],
        outputDescription: 'Separate band-structure figure and DOS figure (one image each), CSV of both curves.',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/band-dos',
        manualEntryFiles: [
          {
            key: 'bandsGnu',
            filename: 'bands.dat.gnu',
            label: 'bands.x .dat.gnu output — paste its content',
            placeholder:
              '0.000000  -5.432100\n0.012345  -5.431000\n0.024690  -5.428200\n...\n' +
              '(blank line between bands)\n\n0.000000  -1.234000\n0.012345  -1.230500\n...',
          },
          {
            key: 'dos',
            filename: 'dos-output.dos',
            label: 'dos.x output — paste its content (keep the EFermi header line if present)',
            placeholder:
              '#  E (eV)   dos(E)     Int dos(E) EFermi =    5.938 eV\n' +
              '-10.000   0.0000   0.0000\n-9.950    0.0012   0.0001\n...',
          },
        ],
      },
      {
        id: 'pdos-plotter',
        title: 'Projected DOS (pDOS) plotter',
        inputFiles: ['projwfc.x pdos_atm output files (one per orbital/atom) — you will label each one after upload'],
        parameters: [
          { id: 'energyShift', label: 'VBM/Fermi energy (eV) — optional if you also upload the dos.x file below, required otherwise', type: 'text', default: '' },
          {
            id: 'figureFormat',
            label: 'Figure format',
            type: 'select',
            options: ['PNG', 'LaTeX (pgfplots)', 'Both'],
            default: 'PNG',
          },
          { id: 'xRange', label: 'X-axis range (optional — auto if left blank)', type: 'text', default: '' },
          { id: 'yRange', label: 'Y-axis range (optional — auto if left blank)', type: 'text', default: '' },
        ],
        outputDescription: 'One figure per species (not stacked into a single panel), combined CSV.',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/pdos-plotter',
      },
      {
        id: 'effective-mass-extractor',
        title: 'Effective mass extractor',
        inputFiles: ['Band-structure data file(s) along one or more k-directions'],
        parameters: [
          { id: 'kDirection', label: 'k-direction(s) (comma-separated)', type: 'text', default: '' },
          { id: 'bandIndex', label: 'Band index', type: 'number', default: 1 },
          { id: 'fitWindow', label: 'Parabolic fit window (k-range)', type: 'text', default: '' },
          {
            id: 'figureFormat',
            label: 'Figure format',
            type: 'select',
            options: ['PNG', 'LaTeX (pgfplots)', 'Both'],
            default: 'PNG',
          },
          { id: 'xRange', label: 'X-axis range (optional — auto if left blank)', type: 'text', default: '' },
          { id: 'yRange', label: 'Y-axis range (optional — auto if left blank)', type: 'text', default: '' },
        ],
        outputDescription: 'Mass table (per direction/carrier type), fit-quality plot.',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/effective-mass',
      },
    ],
  },
  {
    id: 'optical-dielectric',
    name: 'Optical / dielectric properties',
    modules: [
      {
        id: 'dielectric-function-plotter',
        title: 'Dielectric function plotter',
        inputFiles: ['epsilon.x-style real part output', 'epsilon.x-style imaginary part output'],
        parameters: [
          {
            id: 'polarization',
            label: 'Polarization direction',
            type: 'select',
            options: ['Ordinary', 'Extraordinary'],
            default: 'Ordinary',
          },
          {
            id: 'xAxis',
            label: 'X-axis quantity',
            type: 'select',
            options: ['Energy (eV)', 'Wavelength (nm)'],
            default: 'Energy (eV)',
          },
          {
            id: 'figureFormat',
            label: 'Figure format',
            type: 'select',
            options: ['PNG', 'LaTeX (pgfplots)', 'Both'],
            default: 'PNG',
          },
          { id: 'xRange', label: 'X-axis range (optional — auto if left blank; 100,1000 by default for wavelength)', type: 'text', default: '' },
          { id: 'yRange', label: 'Y-axis range (optional — auto if left blank)', type: 'text', default: '' },
        ],
        outputDescription: 'Separate ε1(ω) and ε2(ω) figures (one image each).',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/dielectric-function',
        manualEntryFiles: EPS_MANUAL_ENTRY_FILES,
      },
      {
        id: 'optical-magnitudes-plotter',
        title: 'Optical-magnitudes plotter',
        inputFiles: ['epsilon.x-style real/imaginary part output'],
        parameters: [
          {
            id: 'magnitudes',
            label: 'Magnitude(s) to plot',
            type: 'multiselect',
            options: [
              'Refractive index',
              'Extinction coefficient',
              'Reflectivity',
              'Absorption coefficient',
              'Energy-loss function',
              'Optical conductivity',
            ],
            default: ['Refractive index'],
          },
          {
            id: 'xAxis',
            label: 'X-axis quantity',
            type: 'select',
            options: ['Energy (eV)', 'Wavelength (nm)'],
            default: 'Energy (eV)',
          },
          {
            id: 'figureFormat',
            label: 'Figure format',
            type: 'select',
            options: ['PNG', 'LaTeX (pgfplots)', 'Both'],
            default: 'PNG',
          },
          { id: 'xRange', label: 'X-axis range (optional — auto if left blank; 100,1000 by default for wavelength)', type: 'text', default: '' },
          { id: 'yRange', label: 'Y-axis range (optional — auto if left blank)', type: 'text', default: '' },
        ],
        outputDescription: 'One figure per selected magnitude, plus a combined CSV.',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/optical-magnitudes',
        manualEntryFiles: EPS_MANUAL_ENTRY_FILES,
      },
      {
        id: 'tauc-plot-extractor',
        title: 'Tauc-plot / band-gap extractor',
        inputFiles: ['epsilon.x-style real part output', 'epsilon.x-style imaginary part output'],
        parameters: [
          {
            id: 'approach',
            label: 'Peak-trimming approach — the two can genuinely disagree (trimming can lock onto a low-energy feature instead of the real edge), so both are run independently by default',
            type: 'select',
            options: ['Both approaches (recommended)', 'First approach (no peak-trim)', 'Second approach (peak-trimmed)'],
            default: 'Both approaches (recommended)',
          },
          {
            id: 'transitionType',
            label: 'Transition type',
            type: 'select',
            options: ['Direct', 'Indirect'],
            default: 'Direct',
          },
          { id: 'fitWindow', label: 'Fit window (energy range, optional — auto-detected if left blank)', type: 'text', default: '' },
          { id: 'electronicGap', label: "Material's own DFT electronic (band-structure) gap in eV (optional, but recommended — anchors the automatic search so it doesn't lock onto the wrong absorption feature)", type: 'text', default: '' },
          { id: 'materialLabel', label: 'Material label (optional, shown on the figure)', type: 'text', default: '' },
          {
            id: 'figureFormat',
            label: 'Figure format',
            type: 'select',
            options: ['PNG', 'LaTeX (pgfplots)', 'Both'],
            default: 'PNG',
          },
          { id: 'xRange', label: 'X-axis range (optional — auto if left blank)', type: 'text', default: '' },
          { id: 'yRange', label: 'Y-axis range (optional — auto if left blank)', type: 'text', default: '' },
        ],
        outputDescription: 'Tauc plot(s) with the fitted gap value marked, for one or both peak-trimming approaches, gap value + fit-window summary per approach.',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/tauc-plot',
        manualEntryFiles: EPS_MANUAL_ENTRY_FILES,
      },
    ],
  },
  {
    id: 'charge-bonding',
    name: 'Charge / bonding analysis',
    modules: [
      {
        id: 'bader-charge-analyzer',
        title: 'Bader charge analyzer',
        inputFiles: ['ACF.dat (from the bader code)'],
        parameters: [
          { id: 'elementOrder', label: 'Element per atom, in ACF.dat order (comma-separated, e.g. Zn,Zn,O,O)', type: 'text', default: '' },
          { id: 'valenceElectrons', label: 'Valence electrons per species, from your pseudopotential (e.g. Zn:20,O:6)', type: 'text', default: '' },
          { id: 'formalCharges', label: 'Formal ionic charge per species (e.g. Zn:2,O:-2) — for the ionicity/covalency ratio', type: 'text', default: '' },
        ],
        outputDescription: 'Per-atom table: Bader charge, net charge, ionicity (%) and covalency (%); summary per species.',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/bader-charge',
        manualEntryFiles: [
          {
            key: 'acf',
            filename: 'ACF.dat',
            label: 'ACF.dat content (from the bader code) — paste its content',
            placeholder:
              '#    X       Y       Z       CHARGE     MIN DIST    ATOMIC VOL\n' +
              '  -----------------------------------------------------------------\n' +
              '    1  0.0000  0.0000  0.0000   10.234567    0.500000    12.345678\n' +
              '    2  0.0000  0.0000  3.2500    6.123456    0.450000     9.876543\n' +
              '  -----------------------------------------------------------------\n' +
              '    VACUUM CHARGE:      0.0000\n    VACUUM VOLUME:      0.0000\n' +
              '    NUMBER OF ELECTRONS: 64.0000',
          },
        ],
      },
    ],
  },
]

export function getAllModules() {
  return CATEGORIES.flatMap((category) =>
    category.modules.map((module) => ({ ...module, category: category.name, categoryId: category.id }))
  )
}

export function getModuleById(id) {
  return getAllModules().find((module) => module.id === id) || null
}

export const STATUS_LABELS = {
  candidate: 'Candidate',
  'script-ready': 'Script ready',
  'gui-adopted': 'GUI adopted',
  'standalone-ready': 'Standalone ready',
}
