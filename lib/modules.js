// Single source of truth for every candidate page, mirroring
// Post-Processing-WebApp-Outline.md. Add/edit modules here; the landing
// page and /task/[id] route are generated entirely from this data.
//
// Parameter field types understood by <ParameterForm>: text, number, select,
// multiselect, checkbox.

// Shared by every epsilon.x-based module (dielectric function, optical magnitudes, Tauc):
// the fixed-filename "epsr"/"epsi" keyword each needs to pass the backend's fail-closed
// role check (scripts/common/file_validation.py) when no real upload exists to carry it.
// Sample content below (epsr/epsi, bands.dat.gnu, dos.x) is a decimated slice of real,
// validated bulk-ZnO PBEsol epsilon.x/bands.x/dos.x output from the user's own paper corpus,
// not fabricated placeholder numbers -- it was verified live against this app's production
// API (not just vercel dev) before being wired in here. See [[feedback-test-with-real-data]].
const EPS_SAMPLE_EPSR =
  '# energy grid [eV]     epsr_x  epsr_y  epsr_z\n' +
  '# plasmon frequences [eV]:    14.654525045   14.654521811   14.677708878\n' +
  '0.000000000  563.959673675  563.957450437  992.319123476\n' +
  '0.200333890  -21.613286199  -21.613174807  -44.354073354\n' +
  '0.400667780  -22.500597884  -22.500465452  -36.964313840\n' +
  '0.601001669   -9.222608690   -9.222533240  -20.116938363\n' +
  '0.801335559   -6.097956355   -6.097908871   -9.938928535\n' +
  '1.001669449   -4.944734855   -4.944703059   -3.706891277\n' +
  '1.202003339   -0.831231139   -0.831213241    0.619370847\n' +
  '1.402337229    2.496737038    2.496745302    3.798019142\n' +
  '1.602671119    3.697821125    3.697822948    2.543487682\n' +
  '1.803005008    2.626764802    2.626762876    1.689536522\n' +
  '2.003338898   -0.169661325   -0.169660012    1.668331155\n' +
  '2.203672788    0.448969212    0.448966921   -1.038446790\n' +
  '2.404006678    2.267002269    2.266996182    0.479137891\n' +
  '2.604340568    2.969469157    2.969464920    2.206743143\n' +
  '2.804674457    2.156793025    2.156792265    3.077652457\n' +
  '3.005008347    2.136776347    2.136773614    3.136163382\n' +
  '3.205342237    3.194566297    3.194562370    3.777301629\n' +
  '3.405676127    3.757295391    3.757291542    3.290045999\n' +
  '3.606010017    3.365559651    3.365556540    2.812474931\n' +
  '3.806343907    2.626279015    2.626276466    3.382980212\n' +
  '4.006677796    1.822222342    1.822216079    1.748919999\n' +
  '4.207011686    2.069767150    2.069759896    1.225689206\n' +
  '4.407345576    2.479110458    2.479103599    1.760164139\n' +
  '4.607679466    2.853145883    2.853139588    1.806286383\n' +
  '4.808013356    3.032676589    3.032668841    2.773781911\n' +
  '5.008347245    3.397349489    3.397341039    3.651253035\n' +
  '5.208681135    3.297486885    3.297478604    4.372568735\n' +
  '5.409015025    3.555136490    3.555127236    4.891343743\n' +
  '5.609348915    3.419038458    3.419031352    3.716756029\n' +
  '5.809682805    2.216656487    2.216648438    2.232606178\n' +
  '6.010016694    1.985226537    1.985217653    1.638237303\n' +
  '6.210350584    2.187234356    2.187224021    1.781174940\n' +
  '6.410684474    1.852570217    1.852560033    1.073670092\n' +
  '6.611018364    1.983001380    1.982992318    1.761253984\n' +
  '6.811352254    2.256187700    2.256179869    2.326644377\n' +
  '7.011686144    2.415156841    2.415148990    2.129953978\n' +
  '7.212020033    1.965352923    1.965343696    1.668208689\n' +
  '7.412353923    1.624195058    1.624184111    1.815005767\n' +
  '7.612687813    1.718448243    1.718436264    1.990461481\n' +
  '7.813021703    1.811721645    1.811709104    1.508642724\n' +
  '8.013355593    2.189407156    2.189395536    1.060881279\n' +
  '8.213689482    2.076610740    2.076599878    1.496286671\n' +
  '8.414023372    2.211213099    2.211202019    1.634008749\n' +
  '8.614357262    2.465351404    2.465341057    1.399164665\n' +
  '8.814691152    2.338457603    2.338449596    1.498901420\n' +
  '9.015025042    2.035246003    2.035239411    1.495595956\n' +
  '9.215358932    2.279016088    2.279009266    1.387484930\n' +
  '9.415692821    2.578515107    2.578505682    1.751641082\n' +
  '9.616026711    2.420699216    2.420686896    2.205822359\n' +
  '9.816360601    2.063706165    2.063693589    2.265194546\n' +
  '10.016694491    1.869402703    1.869391629    2.135178417\n' +
  '10.217028381    1.793187497    1.793178286    1.705449667\n' +
  '10.417362270    1.027060858    1.027051381    1.085824327\n' +
  '10.617696160    0.526829600    0.526819220    0.869616147\n' +
  '10.818030050    0.230669670    0.230656965    0.901959583\n' +
  '11.018363940    0.386839882    0.386827497    0.813782592\n' +
  '11.218697830    0.161957071    0.161947089    1.092308469\n' +
  '11.419031720    0.224050687    0.224040173    1.234456789\n' +
  '11.619365609    0.370786399    0.370774256    1.028334696\n' +
  '11.819699499    0.252376694    0.252364495    0.699901830\n' +
  '12.020033389    0.199569315    0.199557560    0.388394179\n' +
  '12.220367279    0.236388521    0.236376591   -0.030701844\n' +
  '12.420701169    0.141913703    0.141901768    0.009628147\n' +
  '12.621035058    0.010439031    0.010426846    0.085701084\n' +
  '12.821368948    0.166286562    0.166273772    0.074938696\n' +
  '13.021702838    0.255247411    0.255234761    0.114276391\n' +
  '13.222036728    0.201583462    0.201571524    0.120585815\n' +
  '13.422370618   -0.083152367   -0.083166080    0.080810357\n' +
  '13.622704508   -0.204307293   -0.204323034   -0.186620843\n' +
  '13.823038397   -0.258126882   -0.258142117   -0.432245311\n' +
  '14.023372287   -0.265900343   -0.265916494   -0.448650841\n' +
  '14.223706177   -0.356499631   -0.356515323   -0.463321400\n' +
  '14.424040067   -0.375506798   -0.375519754   -0.420981713\n' +
  '14.624373957   -0.401277298   -0.401288952   -0.221559945\n' +
  '14.824707846   -0.386389630   -0.386401972   -0.135129233\n' +
  '15.000000000   -0.278046204   -0.278059071   -0.056288832'

const EPS_SAMPLE_EPSI =
  '# energy grid [eV]     epsi_x  epsi_y  epsi_z\n' +
  '#\n' +
  '0.000000000    0.000000000    0.000000000    0.000000000\n' +
  '0.200333890  130.348452762  130.347857875  162.688357221\n' +
  '0.400667780   40.624668964   40.624488082   49.139258458\n' +
  '0.601001669   19.680186639   19.680110984   19.696128270\n' +
  '0.801335559   15.628731477   15.628687306    9.760285943\n' +
  '1.001669449    8.257754675    8.257731296    5.895089332\n' +
  '1.202003339    4.896076215    4.896062548    4.648800574\n' +
  '1.402337229    4.534542186    4.534532280    5.749866661\n' +
  '1.602671119    6.373858193    6.373849593    8.491774119\n' +
  '1.803005008    7.602451023    7.602438531    6.320813669\n' +
  '2.003338898    6.286141814    6.286132447    7.673931872\n' +
  '2.203672788    3.445356729    3.445350314    5.117753458\n' +
  '2.404006678    2.776888007    2.776880585    2.701562630\n' +
  '2.604340568    3.808903029    3.808891306    2.257320558\n' +
  '2.804674457    3.820108122    3.820100179    2.991025228\n' +
  '3.005008347    2.696383291    2.696378338    2.868234536\n' +
  '3.205342237    2.542702612    2.542697256    3.504844473\n' +
  '3.405676127    3.159278020    3.159273106    4.226605390\n' +
  '3.606010017    3.976917651    3.976913347    3.569416586\n' +
  '3.806343907    4.138695851    4.138694303    4.224017501\n' +
  '4.006677796    3.510764594    3.510764267    4.825229488\n' +
  '4.207011686    2.584600677    2.584599018    3.084453288\n' +
  '4.407345576    2.453693630    2.453691934    2.768960294\n' +
  '4.607679466    2.439687084    2.439685228    1.946004165\n' +
  '4.808013356    2.364138170    2.364138185    1.530180120\n' +
  '5.008347245    2.714344472    2.714343587    1.806189871\n' +
  '5.208681135    2.963566031    2.963564685    2.293452544\n' +
  '5.409015025    3.108913168    3.108911153    3.703103644\n' +
  '5.609348915    4.059895337    4.059893031    5.118319436\n' +
  '5.809682805    4.023875793    4.023875842    4.867106844\n' +
  '6.010016694    3.427975804    3.427976182    4.203279640\n' +
  '6.210350584    3.212525689    3.212524955    3.833472829\n' +
  '6.410684474    3.204158657    3.204157562    3.371823948\n' +
  '6.611018364    2.816064360    2.816061563    2.553173867\n' +
  '6.811352254    2.735405811    2.735404517    2.959577427\n' +
  '7.011686144    3.061235731    3.061235818    3.420090174\n' +
  '7.212020033    3.343771972    3.343773505    3.302483573\n' +
  '7.412353923    2.958556077    2.958557096    2.935510441\n' +
  '7.612687813    2.642054271    2.642054726    3.226820385\n' +
  '7.813021703    2.441503791    2.441502531    3.503517308\n' +
  '8.013355593    2.464269840    2.464267542    2.915632088\n' +
  '8.213689482    2.609566437    2.609564126    2.532746521\n' +
  '8.414023372    2.484735734    2.484733472    2.850182048\n' +
  '8.614357262    2.681734346    2.681730302    2.771359623\n' +
  '8.814691152    3.063260893    3.063257238    2.572343333\n' +
  '9.015025042    2.906429903    2.906428495    2.700794759\n' +
  '9.215358932    2.791418021    2.791419101    2.389976870\n' +
  '9.415692821    3.044662523    3.044665503    2.178861039\n' +
  '9.616026711    3.634784273    3.634785835    2.451910603\n' +
  '9.816360601    3.739649555    3.739648894    2.859518533\n' +
  '10.016694491    3.812930372    3.812928470    3.381032804\n' +
  '10.217028381    4.155300895    4.155299654    3.687048583\n' +
  '10.417362270    4.336972784    4.336973601    3.642599562\n' +
  '10.617696160    4.079649588    4.079650821    3.193560660\n' +
  '10.818030050    3.522006697    3.522007845    3.062642012\n' +
  '11.018363940    3.347054379    3.347053351    2.886448782\n' +
  '11.218697830    3.203623554    3.203622408    2.739640768\n' +
  '11.419031720    2.842203091    2.842204392    3.009207154\n' +
  '11.619365609    2.879411717    2.879412552    3.333106716\n' +
  '11.819699499    2.848422151    2.848422279    3.410910215\n' +
  '12.020033389    2.717948933    2.717949064    3.322119767\n' +
  '12.220367279    2.671609276    2.671609566    3.152169770\n' +
  '12.420701169    2.690354251    2.690354714    2.710115208\n' +
  '12.621035058    2.449319590    2.449320484    2.618367849\n' +
  '12.821368948    2.328462341    2.328462880    2.518049661\n' +
  '13.021702838    2.366970980    2.366971494    2.508145815\n' +
  '13.222036728    2.585523565    2.585524749    2.467839602\n' +
  '13.422370618    2.508543958    2.508546415    2.531464095\n' +
  '13.622704508    2.359864690    2.359865845    2.616208769\n' +
  '13.823038397    2.208470858    2.208470827    2.337357446\n' +
  '14.023372287    2.108506550    2.108506296    2.067101667\n' +
  '14.223706177    1.997025510    1.997022281    1.910242285\n' +
  '14.424040067    1.840300471    1.840297305    1.616436592\n' +
  '14.624373957    1.725795322    1.725793899    1.515592922\n' +
  '14.824707846    1.497405157    1.497405171    1.458725833\n' +
  '15.000000000    1.387584891    1.387585180    1.423731708'

const EPS_MANUAL_ENTRY_FILES = [
  {
    key: 'epsr',
    filename: 'epsr_manual.dat',
    label: 'epsilon.x real-part (epsr) output — paste its content',
    placeholder:
      '# E(eV)   eps1_x    eps1_y    eps1_z\n0.000    5.1230    5.1230    4.9870\n' +
      '0.050    5.1300    5.1300    4.9900\n...',
    sampleText: EPS_SAMPLE_EPSR,
  },
  {
    key: 'epsi',
    filename: 'epsi_manual.dat',
    label: 'epsilon.x imaginary-part (epsi) output — paste its content',
    placeholder:
      '# E(eV)   eps2_x    eps2_y    eps2_z\n0.000    0.0010    0.0010    0.0005\n' +
      '0.050    0.0020    0.0020    0.0012\n...',
    sampleText: EPS_SAMPLE_EPSI,
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
      {
        id: 'hubbard-u-reader',
        title: 'Hubbard U (linear response) reader',
        inputFiles: ['hp.x output (the HUBBARD card it prints at the end of a linear-response run)'],
        parameters: [
          { id: 'atomsOrbitals', label: 'Atom/orbital filter (comma-separated substrings, e.g. Zn-3d,O-2p) — optional, shows every U/V value if left blank', type: 'text', default: '' },
        ],
        outputDescription: 'U (and V, if inter-site) value table parsed from the HUBBARD card.',
        compareMode: false,
        status: 'script-ready',
        apiEndpoint: '/api/hubbard-u',
        manualEntryFiles: [
          {
            key: 'hp',
            filename: 'hp-output.out',
            label: 'hp.x output content — paste the HUBBARD card and surrounding text',
            placeholder:
              'HUBBARD (ortho-atomic)\n' +
              'U   Zn-3d   7.4321\n' +
              'U   O-2p    6.1234\n' +
              'V   Zn-3d O-2p  1  2   0.5678\n',
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
