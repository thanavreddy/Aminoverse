// Custom theme colors for AminoVerse using Tailwind CSS
const aminoColors = {
  blue: '#3182CE',
  teal: '#319795',
  // Adding protein visualization colors
  protein: {
    primary: '#FF4D4D',    // Alpha helices
    secondary: '#FFD700',  // Beta sheets
    tertiary: '#4CAF50',   // Loops
    quaternary: '#9C27B0', // Ligands
  },
  // Adding amino acid type colors
  aminoAcid: {
    hydrophobic: '#FF9800',
    polar: '#2196F3',
    positive: '#F44336',
    negative: '#4CAF50',
    special: '#9C27B0',
  },
  // Adding disease association colors
  disease: {
    cancer: '#E53E3E',
    neurological: '#805AD5',
    metabolic: '#38A169',
    cardiovascular: '#DD6B20',
    autoimmune: '#3182CE',
    other: '#718096',
  },
  // DNA and RNA colors
  dna: '#3949AB',
  rna: '#43A047',
  // Visualization background colors
  visualization: {
    background: '#F0F4F8',
    highlight: '#FEFCBF',
    selection: '#B2F5EA',
  },
  gray: {
    100: '#F7FAFC',
    200: '#EDF2F7',
    300: '#E2E8F0',
    400: '#CBD5E0',
    500: '#A0AEC0',
    600: '#718096',
    700: '#4A5568',
    800: '#2D3748',
    900: '#1A202C',
  }
};

// Export our theme values to be used in other parts of the app
const theme = {
  colors: {
    amino: aminoColors
  },
  fonts: {
    heading: 'Inter, system-ui, sans-serif',
    body: 'Inter, system-ui, sans-serif',
    display: 'Montserrat, system-ui, sans-serif',
  },
  sizes: {
    // Custom sizes for protein visualization components
    moleculeViewer: {
      sm: '250px',
      md: '400px',
      lg: '600px',
      xl: '800px',
    }
  },
  // Animation configurations for protein transitions
  animations: {
    folding: {
      duration: '1.5s',
      easing: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
    }
  }
};

export default theme;