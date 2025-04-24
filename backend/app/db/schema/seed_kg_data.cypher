// Clear existing data if needed (uncomment this line with caution in production)
// MATCH (n) DETACH DELETE n;

// Create protein nodes
CREATE (p1:Protein {
  id: "P04637",
  name: "TP53",
  full_name: "Cellular tumor antigen p53",
  function: "Acts as a tumor suppressor by inducing growth arrest or apoptosis depending on the physiological circumstances and cell type.",
  description: "Tumor suppressor that regulates cell division by keeping cells from growing and dividing too fast or in an uncontrolled way."
});

CREATE (p2:Protein {
  id: "P38398",
  name: "BRCA1",
  full_name: "Breast cancer type 1 susceptibility protein",
  function: "Functions in DNA repair, recombination, and cell cycle checkpoint control.",
  description: "Plays a central role in DNA repair by facilitating cellular responses to DNA damage."
});

CREATE (p3:Protein {
  id: "Q00987",
  name: "MDM2",
  full_name: "E3 ubiquitin-protein ligase Mdm2",
  function: "Acts as an E3 ubiquitin ligase that targets tumor suppressor proteins for degradation.",
  description: "Inhibits p53 and p73 tumor suppressors to promote cell survival and growth."
});

CREATE (p4:Protein {
  id: "P00533",
  name: "EGFR",
  full_name: "Epidermal growth factor receptor",
  function: "Receptor tyrosine kinase binding ligands of the EGF family and activating signaling cascades.",
  description: "Cell surface receptor that plays a critical role in cell growth and differentiation."
});

CREATE (p5:Protein {
  id: "P01116",
  name: "KRAS",
  full_name: "GTPase KRas",
  function: "Involved in regulating cell division as a result of growth factor stimulation.",
  description: "Acts as a molecular on/off switch in signaling pathways that control cell growth and differentiation."
});

// Create disease nodes
CREATE (d1:Disease {
  id: "MONDO:0007254",
  name: "Li-Fraumeni syndrome",
  description: "A rare, autosomal dominant cancer predisposition syndrome characterized by early-onset of multiple primary cancers."
});

CREATE (d2:Disease {
  id: "DOID:1612",
  name: "Breast cancer",
  description: "A common malignancy that arises from breast epithelial tissue."
});

CREATE (d3:Disease {
  id: "DOID:1793",
  name: "Pancreatic cancer",
  description: "An aggressive malignancy arising from pancreatic cells with poor prognosis."
});

CREATE (d4:Disease {
  id: "DOID:3908",
  name: "Lung cancer",
  description: "Cancer that begins in the lungs and most often occurs in people who smoke."
});

// Create drug nodes
CREATE (dr1:Drug {
  id: "DB00398",
  name: "Olaparib",
  description: "PARP inhibitor used for the treatment of BRCA-mutated advanced ovarian cancer",
  mechanism: "PARP inhibitor"
});

CREATE (dr2:Drug {
  id: "DB11748",
  name: "Rucaparib",
  description: "PARP inhibitor used for the treatment of ovarian cancer",
  mechanism: "PARP inhibitor"
});

CREATE (dr3:Drug {
  id: "DB00317",
  name: "Gefitinib",
  description: "EGFR inhibitor used for the treatment of certain types of lung cancer",
  mechanism: "EGFR tyrosine kinase inhibitor"
});

// Create relationships
// Protein-Protein interactions
CREATE (p1)-[:INTERACTS_WITH {score: 0.9, type: "binds"}]->(p3);
CREATE (p1)-[:INTERACTS_WITH {score: 0.7, type: "regulates"}]->(p2);
CREATE (p2)-[:INTERACTS_WITH {score: 0.8, type: "cooperates"}]->(p1);
CREATE (p4)-[:INTERACTS_WITH {score: 0.85, type: "activates"}]->(p5);
CREATE (p5)-[:INTERACTS_WITH {score: 0.75, type: "signals"}]->(p1);
CREATE (p4)-[:INTERACTS_WITH {score: 0.65, type: "phosphorylates"}]->(p2);

// Protein-Disease associations
CREATE (p1)-[:ASSOCIATED_WITH {evidence: "numerous studies", strength: "strong"}]->(d1);
CREATE (p1)-[:ASSOCIATED_WITH {evidence: "published research", strength: "moderate"}]->(d3);
CREATE (p2)-[:ASSOCIATED_WITH {evidence: "genetic studies", strength: "strong"}]->(d2);
CREATE (p4)-[:ASSOCIATED_WITH {evidence: "clinical data", strength: "strong"}]->(d4);
CREATE (p5)-[:ASSOCIATED_WITH {evidence: "mutation analysis", strength: "strong"}]->(d3);

// Drug-Protein targeting
CREATE (dr1)-[:TARGETS {mechanism: "inhibition", affinity: 5.2}]->(p2);
CREATE (dr2)-[:TARGETS {mechanism: "inhibition", affinity: 7.8}]->(p2);
CREATE (dr3)-[:TARGETS {mechanism: "inhibition", affinity: 2.4}]->(p4);

// Create structure data
CREATE (s1:Structure {
  pdb_id: "1TUP",
  method: "X-ray diffraction",
  resolution: 2.2,
  release_date: "1994-09-15"
});

CREATE (s2:Structure {
  alphafold_id: "AF-P38398-F1",
  confidence: "high",
  prediction_date: "2021-07-22"
});

CREATE (s3:Structure {
  pdb_id: "4R6E",
  method: "X-ray diffraction",
  resolution: 1.8,
  release_date: "2015-02-10"
});

CREATE (s4:Structure {
  alphafold_id: "AF-P00533-F1",
  confidence: "high",
  prediction_date: "2021-07-22"
});

// Connect proteins to their structures
CREATE (p1)-[:HAS_STRUCTURE]->(s1);
CREATE (p2)-[:HAS_STRUCTURE]->(s2);
CREATE (p3)-[:HAS_STRUCTURE]->(s3);
CREATE (p4)-[:HAS_STRUCTURE]->(s4);

// Create indexes for better query performance
CREATE INDEX protein_id IF NOT EXISTS FOR (p:Protein) ON (p.id);
CREATE INDEX disease_id IF NOT EXISTS FOR (d:Disease) ON (d.id);
CREATE INDEX drug_id IF NOT EXISTS FOR (dr:Drug) ON (dr.id);
CREATE INDEX structure_id IF NOT EXISTS FOR (s:Structure) ON (s.pdb_id);