import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  calculateCommunityMetricsFromStates,
  METRIC_KEYS,
} from "./radar_plot.js";

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x08111d, 18, 40);

const camera = new THREE.PerspectiveCamera(
  60,
  window.innerWidth / window.innerHeight,
  0.1,
  100
);
camera.position.set(0, 6.5, 10);
camera.lookAt(0, 0, 0);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.outputColorSpace = THREE.SRGBColorSpace;
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.target.set(0, 0, 0);
controls.enablePan = false;
controls.minDistance = 4;
controls.maxDistance = 24;
controls.maxPolarAngle = Math.PI / 2 - 0.05;
controls.update();

scene.add(new THREE.AmbientLight(0xbfd8ff, 0.85));

const directionalLight = new THREE.DirectionalLight(0xffffff, 1.4);
directionalLight.position.set(6, 10, 8);
scene.add(directionalLight);

const planeSize = 7;
const cubeSize = 2.2;
const cubeHeight = cubeSize / 3;
const towerFootprint = cubeSize * 0.85;
const towerHeight = cubeSize * 2;
const quadrantStateOrder = ["empty", "public space", "podium", "tower"];
const squareFootByType = {
  empty: 0,
  "public space": 625,
  podium: 2500,
  tower: 65000,
};
const secondaryUseOptions = {
  empty: [],
  "public space": ["park", "plaza"],
  podium: ["retail", "cafe"],
  tower: ["office", "housing"],
};
const hourlyActivityProbabilities = {
  0: { Home: 0.92, Office: 0.0, Shopping: 0.0, Cafe: 0.0, Park: 0.0, Plaza: 0.0, Other: 0.08 },
  1: { Home: 0.93, Office: 0.0, Shopping: 0.0, Cafe: 0.0, Park: 0.0, Plaza: 0.0, Other: 0.07 },
  2: { Home: 0.94, Office: 0.0, Shopping: 0.0, Cafe: 0.0, Park: 0.0, Plaza: 0.0, Other: 0.06 },
  3: { Home: 0.95, Office: 0.0, Shopping: 0.0, Cafe: 0.0, Park: 0.0, Plaza: 0.0, Other: 0.05 },
  4: { Home: 0.95, Office: 0.0, Shopping: 0.0, Cafe: 0.0, Park: 0.0, Plaza: 0.0, Other: 0.05 },
  5: { Home: 0.93, Office: 0.0, Shopping: 0.0, Cafe: 0.0, Park: 0.01, Plaza: 0.0, Other: 0.06 },
  6: { Home: 0.88, Office: 0.0, Shopping: 0.0, Cafe: 0.02, Park: 0.03, Plaza: 0.0, Other: 0.07 },
  7: { Home: 0.72, Office: 0.05, Shopping: 0.0, Cafe: 0.08, Park: 0.06, Plaza: 0.01, Other: 0.08 },
  8: { Home: 0.35, Office: 0.25, Shopping: 0.02, Cafe: 0.2, Park: 0.05, Plaza: 0.02, Other: 0.11 },
  9: { Home: 0.1, Office: 0.7, Shopping: 0.02, Cafe: 0.08, Park: 0.03, Plaza: 0.02, Other: 0.05 },
  10: { Home: 0.1, Office: 0.72, Shopping: 0.03, Cafe: 0.04, Park: 0.04, Plaza: 0.02, Other: 0.05 },
  11: { Home: 0.1, Office: 0.65, Shopping: 0.05, Cafe: 0.05, Park: 0.05, Plaza: 0.03, Other: 0.07 },
  12: { Home: 0.1, Office: 0.55, Shopping: 0.08, Cafe: 0.12, Park: 0.05, Plaza: 0.05, Other: 0.05 },
  13: { Home: 0.1, Office: 0.65, Shopping: 0.06, Cafe: 0.08, Park: 0.04, Plaza: 0.04, Other: 0.03 },
  14: { Home: 0.1, Office: 0.72, Shopping: 0.05, Cafe: 0.04, Park: 0.03, Plaza: 0.03, Other: 0.03 },
  15: { Home: 0.1, Office: 0.72, Shopping: 0.06, Cafe: 0.04, Park: 0.03, Plaza: 0.03, Other: 0.02 },
  16: { Home: 0.1, Office: 0.7, Shopping: 0.06, Cafe: 0.04, Park: 0.03, Plaza: 0.03, Other: 0.04 },
  17: { Home: 0.2, Office: 0.5, Shopping: 0.1, Cafe: 0.05, Park: 0.06, Plaza: 0.05, Other: 0.04 },
  18: { Home: 0.45, Office: 0.15, Shopping: 0.12, Cafe: 0.06, Park: 0.1, Plaza: 0.07, Other: 0.05 },
  19: { Home: 0.6, Office: 0.05, Shopping: 0.1, Cafe: 0.05, Park: 0.1, Plaza: 0.06, Other: 0.04 },
  20: { Home: 0.7, Office: 0.02, Shopping: 0.08, Cafe: 0.04, Park: 0.08, Plaza: 0.05, Other: 0.03 },
  21: { Home: 0.78, Office: 0.01, Shopping: 0.05, Cafe: 0.03, Park: 0.06, Plaza: 0.04, Other: 0.03 },
  22: { Home: 0.84, Office: 0.01, Shopping: 0.03, Cafe: 0.02, Park: 0.04, Plaza: 0.03, Other: 0.03 },
  23: { Home: 0.89, Office: 0.0, Shopping: 0.01, Cafe: 0.01, Park: 0.02, Plaza: 0.02, Other: 0.05 },
};
let buildingOpacity = 1;

const transparencySlider = document.getElementById("transparency-slider");
const transparencyValue = document.getElementById("transparency-value");
const timeSlider = document.getElementById("time-slider");
const timeValue = document.getElementById("time-value");
const radarChart = document.getElementById("radar-chart");
const pieChart = document.getElementById("pie-chart");
let timeOfDay = 0;

const quadrantCenters = {
  northwest: new THREE.Vector3(-planeSize / 4, 0, planeSize / 4),
  northeast: new THREE.Vector3(planeSize / 4, 0, planeSize / 4),
  southwest: new THREE.Vector3(-planeSize / 4, 0, -planeSize / 4),
  southeast: new THREE.Vector3(planeSize / 4, 0, -planeSize / 4),
};

const planeGeometry = new THREE.PlaneGeometry(planeSize, planeSize);
const planeMaterial = new THREE.MeshStandardMaterial({
  color: 0x68b7ff,
  side: THREE.DoubleSide,
  metalness: 0.1,
  roughness: 0.72,
});
const plane = new THREE.Mesh(planeGeometry, planeMaterial);
plane.rotation.x = -Math.PI / 2;
scene.add(plane);

const offSiteGeometry = new THREE.PlaneGeometry(planeSize / 2, planeSize / 2);
const offSiteMaterial = new THREE.MeshStandardMaterial({
  color: 0x5a6f86,
  side: THREE.DoubleSide,
  metalness: 0.08,
  roughness: 0.78,
});
const offSitePlane = new THREE.Mesh(offSiteGeometry, offSiteMaterial);
offSitePlane.rotation.x = -Math.PI / 2;
offSitePlane.position.set(-planeSize * 0.78, 0, 0);
scene.add(offSitePlane);
const offSiteCenter = offSitePlane.position.clone();
const quadrantSize = planeSize / 2;

const dividerMaterial = new THREE.LineBasicMaterial({ color: 0xe8f1ff });
const dividerGeometry = new THREE.BufferGeometry().setFromPoints([
  new THREE.Vector3(-planeSize / 2, 0.03, 0),
  new THREE.Vector3(planeSize / 2, 0.03, 0),
  new THREE.Vector3(0, 0.03, -planeSize / 2),
  new THREE.Vector3(0, 0.03, planeSize / 2),
]);
const dividers = new THREE.LineSegments(dividerGeometry, dividerMaterial);
scene.add(dividers);

function createGroundLabel(primaryText, secondaryText, width, bgColor, textColor) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;

  const context = canvas.getContext("2d");
  context.fillStyle = bgColor;
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = textColor;
  context.textAlign = "center";
  context.textBaseline = "alphabetic";
  context.font = "bold 92px Segoe UI";
  context.fillText(primaryText, canvas.width / 2, 220);
  context.font = "600 56px Segoe UI";
  context.fillText(secondaryText, canvas.width / 2, 320);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;

  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
  });
  const geometry = new THREE.PlaneGeometry(width, width);
  const label = new THREE.Mesh(geometry, material);
  label.rotation.x = -Math.PI / 2;
  label.userData.isAdjustableOpacity = true;
  label.userData.baseOpacity = 1;
  label.material.opacity = buildingOpacity;

  return label;
}

function createQuadrantNumberLabel(text) {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;

  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#f3f7ff";
  context.font = "bold 132px Segoe UI";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text, canvas.width / 2, canvas.height / 2);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;

  const material = new THREE.MeshBasicMaterial({
    map: texture,
    transparent: true,
  });
  const geometry = new THREE.PlaneGeometry(0.55, 0.55);
  const label = new THREE.Mesh(geometry, material);
  label.rotation.x = -Math.PI / 2;

  return label;
}

function markAdjustableOpacity(mesh, baseOpacity = 1) {
  mesh.userData.isAdjustableOpacity = true;
  mesh.userData.baseOpacity = baseOpacity;
  mesh.material.transparent = true;
  mesh.material.opacity = baseOpacity * buildingOpacity;
  return mesh;
}

function applyBuildingOpacity(root) {
  root.traverse((child) => {
    if (!child.isMesh || !child.userData.isAdjustableOpacity) {
      return;
    }

    const baseOpacity = child.userData.baseOpacity ?? 1;
    child.material.transparent = true;
    child.material.opacity = baseOpacity * buildingOpacity;
  });
}

function createPodiumTemplate(center, secondaryText) {
  const group = new THREE.Group();

  const cubeGeometry = new THREE.BoxGeometry(cubeSize, cubeHeight, cubeSize);
  const cubeMaterial = new THREE.MeshStandardMaterial({
    color: 0xffb347,
    metalness: 0.15,
    roughness: 0.55,
  });
  const cube = markAdjustableOpacity(new THREE.Mesh(cubeGeometry, cubeMaterial));
  cube.position.set(0, cubeHeight / 2, 0);
  group.add(cube);

  const label = createGroundLabel(
    "podium",
    secondaryText,
    cubeSize * 0.95,
    "#f6d7a8",
    "#1a2230"
  );
  label.position.set(0, cubeHeight + 0.01, 0);
  group.add(label);

  group.position.copy(center);
  return group;
}

function createTowerTemplate(center, secondaryText) {
  const group = new THREE.Group();

  const towerGeometry = new THREE.BoxGeometry(
    towerFootprint,
    towerHeight,
    towerFootprint
  );
  const towerMaterial = new THREE.MeshStandardMaterial({
    color: 0x9adf9a,
    metalness: 0.12,
    roughness: 0.58,
  });
  const tower = markAdjustableOpacity(new THREE.Mesh(towerGeometry, towerMaterial));
  tower.position.set(0, towerHeight / 2, 0);
  group.add(tower);

  const label = createGroundLabel(
    "tower",
    secondaryText,
    towerFootprint * 0.95,
    "#d9f3d6",
    "#183020"
  );
  label.position.set(0, towerHeight + 0.01, 0);
  group.add(label);

  group.position.copy(center);
  return group;
}

function createTree(x, z) {
  const tree = new THREE.Group();
  const trunkHeight = 0.55;
  const trunkRadius = 0.12;

  const trunkGeometry = new THREE.CylinderGeometry(
    trunkRadius,
    trunkRadius,
    trunkHeight,
    20
  );
  const trunkMaterial = new THREE.MeshStandardMaterial({
    color: 0x7a4b2a,
    roughness: 0.9,
  });
  const trunk = markAdjustableOpacity(new THREE.Mesh(trunkGeometry, trunkMaterial));
  trunk.position.set(x, trunkHeight / 2, z);
  tree.add(trunk);

  const leavesRadius = 0.33;
  const leavesGeometry = new THREE.SphereGeometry(leavesRadius, 24, 24);
  const leavesMaterial = new THREE.MeshStandardMaterial({
    color: 0x59b85f,
    roughness: 0.85,
  });
  const leaves = markAdjustableOpacity(new THREE.Mesh(leavesGeometry, leavesMaterial));
  leaves.position.set(x, trunkHeight + leavesRadius * 0.9, z);
  tree.add(leaves);

  return tree;
}

function createParkTemplate(center, secondaryText) {
  const group = new THREE.Group();

  group.add(createTree(-0.85, -0.7));
  group.add(createTree(0.8, -0.65));
  group.add(createTree(-0.75, 0.8));
  group.add(createTree(0.85, 0.75));

  const label = createGroundLabel(
    "public space",
    secondaryText,
    cubeSize * 1.1,
    "#d8f0d3",
    "#1d3420"
  );
  label.position.set(0, 0.02, 0);
  group.add(label);

  group.position.copy(center);
  return group;
}

function createEmptyTemplate(center) {
  const group = new THREE.Group();
  const label = createGroundLabel(
    "empty",
    "",
    cubeSize * 1.1,
    "#d9e3ee",
    "#233042"
  );
  label.position.set(0, 0.02, 0);
  group.add(label);
  group.position.copy(center);
  return group;
}

const offSiteLabel = createGroundLabel(
  "off site",
  "",
  planeSize / 2.4,
  "#c7d3df",
  "#233042"
);
offSiteLabel.position.set(-planeSize * 0.78, 0.02, 0);
scene.add(offSiteLabel);

const quadrantTemplates = {
  podium: (center, secondaryText) => createPodiumTemplate(center, secondaryText),
  tower: (center, secondaryText) => createTowerTemplate(center, secondaryText),
  "public space": (center, secondaryText) => createParkTemplate(center, secondaryText),
  empty: (center) => createEmptyTemplate(center),
};

const quadrantPrimaryStates = {
  northwest: "empty",
  northeast: "empty",
  southwest: "empty",
  southeast: "empty",
};
const quadrantSecondaryStates = {
  northwest: "",
  northeast: "",
  southwest: "",
  southeast: "",
};

const quadrantSquareFootage = {};

const deployedQuadrants = {};
const radarMetricLabels = {
  usageDiversity: ["Usage", "Diversity"],
  economicVibrancy: ["Economic", "Vibrancy"],
  thirdSpaces: ["Third", "Spaces"],
  housingAffordability: ["Housing", "Affordability"],
  emissionReduction: ["Emission", "Reduction"],
};
const usageTypeColors = {
  Home: "#7cc7ff",
  Office: "#ffd166",
  Shopping: "#ff8fab",
  Cafe: "#cdb4db",
  Park: "#7bd389",
  Plaza: "#a0c4ff",
  Other: "#9aa6b2",
};
const agentCount = 10;
const agentLocationAnchors = {
  offSite: { center: offSiteCenter, size: quadrantSize },
  northwest: { center: quadrantCenters.northwest, size: quadrantSize },
  northeast: { center: quadrantCenters.northeast, size: quadrantSize },
  southwest: { center: quadrantCenters.southwest, size: quadrantSize },
  southeast: { center: quadrantCenters.southeast, size: quadrantSize },
};
const agents = [];

function deployQuadrant(quadrantKey) {
  const existingGroup = deployedQuadrants[quadrantKey];

  if (existingGroup) {
    scene.remove(existingGroup);
  }

  const primaryState = quadrantPrimaryStates[quadrantKey];
  const secondaryState = quadrantSecondaryStates[quadrantKey];
  quadrantSquareFootage[quadrantKey] = squareFootByType[primaryState];
  const center = quadrantCenters[quadrantKey];
  const nextGroup = quadrantTemplates[primaryState](center, secondaryState);
  applyBuildingOpacity(nextGroup);
  deployedQuadrants[quadrantKey] = nextGroup;
  scene.add(nextGroup);
}

function createAgent(agentId) {
  const agentGeometry = new THREE.CircleGeometry(0.12, 24);
  const agentMaterial = new THREE.MeshBasicMaterial({
    color: 0xff4d4d,
  });
  const agentMesh = new THREE.Mesh(agentGeometry, agentMaterial);
  agentMesh.rotation.x = -Math.PI / 2;
  scene.add(agentMesh);

  return {
    id: agentId,
    mesh: agentMesh,
    currentActivity: "Other",
    currentDestination: "offSite",
  };
}

function getCommunitySignature() {
  return Object.keys(quadrantPrimaryStates)
    .map(
      (quadrantKey) =>
        `${quadrantKey}:${quadrantPrimaryStates[quadrantKey]}:${quadrantSecondaryStates[quadrantKey]}`
    )
    .join("|");
}

function deterministicRandom(seedString) {
  let hash = 2166136261;

  for (let index = 0; index < seedString.length; index += 1) {
    hash ^= seedString.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  return ((hash >>> 0) % 1000000) / 1000000;
}

function getAvailableDestinationsByActivity() {
  const destinations = {
    Home: [],
    Office: [],
    Shopping: [],
    Cafe: [],
    Park: [],
    Plaza: [],
    Other: ["offSite"],
  };

  Object.keys(quadrantPrimaryStates).forEach((quadrantKey) => {
    const primaryState = quadrantPrimaryStates[quadrantKey];
    const secondaryState = quadrantSecondaryStates[quadrantKey];

    if (secondaryState === "housing") {
      destinations.Home.push(quadrantKey);
    }

    if (secondaryState === "office") {
      destinations.Office.push(quadrantKey);
    }

    if (secondaryState === "retail") {
      destinations.Shopping.push(quadrantKey);
    }

    if (secondaryState === "cafe") {
      destinations.Cafe.push(quadrantKey);
    }

    if (primaryState === "public space" && secondaryState === "park") {
      destinations.Park.push(quadrantKey);
    }

    if (primaryState === "public space" && secondaryState === "plaza") {
      destinations.Plaza.push(quadrantKey);
    }
  });

  return destinations;
}

function sampleWeightedActivity(probabilityMap, seedValue) {
  const weightedEntries = Object.entries(probabilityMap).filter(
    ([, probability]) => probability > 0
  );

  const probabilityTotal = weightedEntries.reduce(
    (sum, [, probability]) => sum + probability,
    0
  );

  if (probabilityTotal <= 0) {
    return "Other";
  }

  let runningTotal = 0;

  for (const [activity, probability] of weightedEntries) {
    runningTotal += probability / probabilityTotal;
    if (seedValue <= runningTotal) {
      return activity;
    }
  }

  return weightedEntries[weightedEntries.length - 1][0];
}

function getAgentDestinationKey(agent, hour) {
  const hourlyProbabilities = hourlyActivityProbabilities[hour] ?? hourlyActivityProbabilities[0];
  const availableDestinations = getAvailableDestinationsByActivity();
  const communitySignature = getCommunitySignature();
  const activitySeed = deterministicRandom(`activity|${agent.id}|${hour}|${communitySignature}`);
  const activity = sampleWeightedActivity(hourlyProbabilities, activitySeed);
  const destinationOptions = availableDestinations[activity] ?? ["offSite"];

  agent.currentActivity = destinationOptions.length === 0 ? "Other" : activity;

  if (destinationOptions.length === 0) {
    agent.currentDestination = "offSite";
    return "offSite";
  }

  const locationSeed = deterministicRandom(`location|${agent.id}|${hour}|${communitySignature}`);
  const destinationIndex = Math.floor(locationSeed * destinationOptions.length);
  const destinationKey =
    destinationOptions[Math.min(destinationIndex, destinationOptions.length - 1)];
  agent.currentDestination = destinationKey;
  return destinationKey;
}

function getAgentSlotPosition(locationCenter, squareSize, slotIndex) {
  const margin = 0.35;
  const spacing = 0.38;
  const usableWidth = squareSize - margin * 2;
  const columns = Math.max(1, Math.floor(usableWidth / spacing) + 1);
  const columnIndex = slotIndex % columns;
  const rowIndex = Math.floor(slotIndex / columns);
  const startX = locationCenter.x - squareSize / 2 + margin;
  const startZ = locationCenter.z + squareSize / 2 - margin;

  return new THREE.Vector3(
    startX + columnIndex * spacing,
    0.05,
    startZ - rowIndex * spacing
  );
}

function updateAgentPositions() {
  const agentsByDestination = {};

  agents.forEach((agent) => {
    const destinationKey = getAgentDestinationKey(agent, timeOfDay);
    if (!agentsByDestination[destinationKey]) {
      agentsByDestination[destinationKey] = [];
    }
    agentsByDestination[destinationKey].push(agent);
  });

  Object.entries(agentsByDestination).forEach(([destinationKey, destinationAgents]) => {
    const anchor = agentLocationAnchors[destinationKey] ?? agentLocationAnchors.offSite;

    destinationAgents.forEach((agent, slotIndex) => {
      const position = getAgentSlotPosition(anchor.center, anchor.size, slotIndex);
      agent.mesh.position.copy(position);
    });
  });
}

function resetSecondaryStateForQuadrant(quadrantKey) {
  const primaryState = quadrantPrimaryStates[quadrantKey];
  const options = secondaryUseOptions[primaryState];
  quadrantSecondaryStates[quadrantKey] = options.length > 0 ? options[0] : "";
}

Object.keys(quadrantPrimaryStates).forEach((quadrantKey) => {
  resetSecondaryStateForQuadrant(quadrantKey);
});

Object.keys(quadrantPrimaryStates).forEach((quadrantKey) => {
  deployQuadrant(quadrantKey);
});

for (let agentIndex = 0; agentIndex < agentCount; agentIndex += 1) {
  agents.push(createAgent(agentIndex));
}

const quadrantNumberLabels = [
  { text: "1", position: new THREE.Vector3(-0.45, 0.03, -0.45) },
  { text: "2", position: new THREE.Vector3(0.45, 0.03, -0.45) },
  { text: "3", position: new THREE.Vector3(-0.45, 0.03, 0.45) },
  { text: "4", position: new THREE.Vector3(0.45, 0.03, 0.45) },
];

quadrantNumberLabels.forEach(({ text, position }) => {
  const label = createQuadrantNumberLabel(text);
  label.position.copy(position);
  scene.add(label);
});

const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let pointerDownPosition = null;

function getQuadrantKeyFromPoint(point) {
  if (point.x < 0 && point.z > 0) {
    return "northwest";
  }

  if (point.x >= 0 && point.z > 0) {
    return "northeast";
  }

  if (point.x < 0 && point.z <= 0) {
    return "southwest";
  }

  return "southeast";
}

function cycleQuadrantState(quadrantKey) {
  const currentState = quadrantPrimaryStates[quadrantKey];
  const currentIndex = quadrantStateOrder.indexOf(currentState);
  const nextIndex = (currentIndex + 1) % quadrantStateOrder.length;
  quadrantPrimaryStates[quadrantKey] = quadrantStateOrder[nextIndex];
  resetSecondaryStateForQuadrant(quadrantKey);
  deployQuadrant(quadrantKey);
  updateAgentPositions();
  renderRadarChart();
  renderPieChart();
  renderScene();
}

function cycleQuadrantSecondaryState(quadrantKey) {
  const primaryState = quadrantPrimaryStates[quadrantKey];
  const options = secondaryUseOptions[primaryState];

  if (!options || options.length === 0) {
    return;
  }

  const currentSecondaryState = quadrantSecondaryStates[quadrantKey];
  const currentIndex = options.indexOf(currentSecondaryState);
  const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % options.length : 0;
  quadrantSecondaryStates[quadrantKey] = options[nextIndex];
  deployQuadrant(quadrantKey);
  updateAgentPositions();
  renderRadarChart();
  renderPieChart();
  renderScene();
}

function getQuadrantSquareFootage(quadrantKey) {
  return quadrantSquareFootage[quadrantKey] ?? 0;
}

function getCanvasRelativePointer(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function updateRaycasterFromEvent(event) {
  const rect = renderer.domElement.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
}

function getClickedQuadrantKey(event) {
  updateRaycasterFromEvent(event);
  const intersections = raycaster.intersectObject(plane, false);

  if (intersections.length === 0) {
    return null;
  }

  const hitPoint = intersections[0].point;
  const halfPlane = planeSize / 2;

  if (
    hitPoint.x < -halfPlane ||
    hitPoint.x > halfPlane ||
    hitPoint.z < -halfPlane ||
    hitPoint.z > halfPlane
  ) {
    return null;
  }

  return getQuadrantKeyFromPoint(hitPoint);
}

const grid = new THREE.GridHelper(18, 18, 0x7fb8ff, 0x24425f);
grid.position.y = -0.9;
scene.add(grid);

function renderScene() {
  renderer.render(scene, camera);
}

function getRadarPoint(index, value, radius, centerX, centerY) {
  const angle = -Math.PI / 2 + (index / METRIC_KEYS.length) * Math.PI * 2;
  const scaledRadius = radius * (value / 100);
  return {
    x: centerX + Math.cos(angle) * scaledRadius,
    y: centerY + Math.sin(angle) * scaledRadius,
  };
}

function createSvgNode(tagName, attributes) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", tagName);

  Object.entries(attributes).forEach(([key, value]) => {
    node.setAttribute(key, String(value));
  });

  return node;
}

function polarToCartesian(centerX, centerY, radius, angleRadians) {
  return {
    x: centerX + Math.cos(angleRadians) * radius,
    y: centerY + Math.sin(angleRadians) * radius,
  };
}

function describePieSlice(centerX, centerY, radius, startAngle, endAngle) {
  const start = polarToCartesian(centerX, centerY, radius, startAngle);
  const end = polarToCartesian(centerX, centerY, radius, endAngle);
  const largeArcFlag = endAngle - startAngle > Math.PI ? 1 : 0;

  return [
    `M ${centerX} ${centerY}`,
    `L ${start.x} ${start.y}`,
    `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${end.x} ${end.y}`,
    "Z",
  ].join(" ");
}

function renderRadarChart() {
  const metricsResult = calculateCommunityMetricsFromStates(
    quadrantPrimaryStates,
    quadrantSecondaryStates
  );
  const metrics = metricsResult.normalizedMetrics;
  const centerX = 160;
  const centerY = 165;
  const radius = 92;

  radarChart.replaceChildren();

  [0.25, 0.5, 0.75, 1].forEach((step) => {
    const ringPoints = METRIC_KEYS.map((metricKey, index) => {
      const point = getRadarPoint(index, step * 100, radius, centerX, centerY);
      return `${point.x},${point.y}`;
    }).join(" ");

    radarChart.appendChild(
      createSvgNode("polygon", {
        points: ringPoints,
        fill: "none",
        stroke: "rgba(210, 226, 255, 0.24)",
        "stroke-width": 1,
      })
    );
  });

  METRIC_KEYS.forEach((metricKey, index) => {
    const axisPoint = getRadarPoint(index, 100, radius, centerX, centerY);
    radarChart.appendChild(
      createSvgNode("line", {
        x1: centerX,
        y1: centerY,
        x2: axisPoint.x,
        y2: axisPoint.y,
        stroke: "rgba(210, 226, 255, 0.28)",
        "stroke-width": 1,
      })
    );

    const labelPoint = getRadarPoint(index, 112, radius, centerX, centerY);
    const labelLines = radarMetricLabels[metricKey];
    const text = createSvgNode("text", {
      x: labelPoint.x,
      y: labelPoint.y,
      fill: "#e8f1ff",
      "font-size": 10,
      "font-weight": 600,
      "text-anchor":
        labelPoint.x < centerX - 6
          ? "end"
          : labelPoint.x > centerX + 6
            ? "start"
            : "middle",
      "dominant-baseline":
        labelPoint.y < centerY - 6
          ? "auto"
          : labelPoint.y > centerY + 6
            ? "hanging"
            : "middle",
    });
    labelLines.forEach((line, lineIndex) => {
      const tspan = createSvgNode("tspan", {
        x: labelPoint.x,
        dy: lineIndex === 0 ? 0 : 12,
      });
      tspan.textContent = line;
      text.appendChild(tspan);
    });
    radarChart.appendChild(text);
  });

  const metricPolygonPoints = METRIC_KEYS.map((metricKey, index) => {
    const point = getRadarPoint(index, metrics[metricKey], radius, centerX, centerY);
    return `${point.x},${point.y}`;
  }).join(" ");

  radarChart.appendChild(
    createSvgNode("polygon", {
      points: metricPolygonPoints,
      fill: "rgba(104, 183, 255, 0.28)",
      stroke: "#8cc8ff",
      "stroke-width": 2,
    })
  );

  METRIC_KEYS.forEach((metricKey, index) => {
    const point = getRadarPoint(index, metrics[metricKey], radius, centerX, centerY);

    radarChart.appendChild(
      createSvgNode("circle", {
        cx: point.x,
        cy: point.y,
        r: 3.5,
        fill: "#dff2ff",
      })
    );

    const valueText = createSvgNode("text", {
      x: point.x,
      y: point.y - 8,
      fill: "#dff2ff",
      "font-size": 10,
      "text-anchor": "middle",
    });
    valueText.textContent = `${metrics[metricKey]}`;
    radarChart.appendChild(valueText);
  });
}

function renderPieChart() {
  pieChart.replaceChildren();

  const counts = {
    Home: 0,
    Office: 0,
    Shopping: 0,
    Cafe: 0,
    Park: 0,
    Plaza: 0,
    Other: 0,
  };

  agents.forEach((agent) => {
    counts[agent.currentActivity] += 1;
  });

  const entries = Object.entries(counts).filter(([, count]) => count > 0);
  const centerX = 82;
  const centerY = 86;
  const radius = 52;
  let startAngle = -Math.PI / 2;

  entries.forEach(([usageType, count]) => {
    const fraction = count / agentCount;
    const endAngle = startAngle + fraction * Math.PI * 2;
    pieChart.appendChild(
      createSvgNode("path", {
        d: describePieSlice(centerX, centerY, radius, startAngle, endAngle),
        fill: usageTypeColors[usageType],
        stroke: "rgba(8, 12, 20, 0.65)",
        "stroke-width": 1,
      })
    );
    startAngle = endAngle;
  });

  pieChart.appendChild(
    createSvgNode("circle", {
      cx: centerX,
      cy: centerY,
      r: 22,
      fill: "rgba(8, 12, 20, 0.9)",
    })
  );

  const countText = createSvgNode("text", {
    x: centerX,
    y: centerY - 2,
    fill: "#e8f1ff",
    "font-size": 10,
    "text-anchor": "middle",
  });
  countText.textContent = `${agentCount}`;
  pieChart.appendChild(countText);

  const agentsText = createSvgNode("text", {
    x: centerX,
    y: centerY + 12,
    fill: "#b9cae3",
    "font-size": 8,
    "text-anchor": "middle",
  });
  agentsText.textContent = "agents";
  pieChart.appendChild(agentsText);

  entries.forEach(([usageType, count], index) => {
    const legendY = 26 + index * 20;
    pieChart.appendChild(
      createSvgNode("rect", {
        x: 165,
        y: legendY - 10,
        width: 10,
        height: 10,
        rx: 2,
        fill: usageTypeColors[usageType],
      })
    );

    const label = createSvgNode("text", {
      x: 182,
      y: legendY,
      fill: "#e8f1ff",
      "font-size": 10,
    });
    label.textContent = `${usageType} ${Math.round((count / agentCount) * 100)}%`;
    pieChart.appendChild(label);
  });
}

function updateBuildingTransparency(value) {
  buildingOpacity = value;
  transparencyValue.textContent = `${Math.round(value * 100)}%`;
  Object.values(deployedQuadrants).forEach((quadrantGroup) => {
    applyBuildingOpacity(quadrantGroup);
  });
  renderScene();
}

function formatHourLabel(hour) {
  if (hour === 0) {
    return "12am";
  }

  if (hour < 12) {
    return `${hour}am`;
  }

  if (hour === 12) {
    return "12pm";
  }

  return `${hour - 12}pm`;
}

function updateTimeOfDay(hour) {
  timeOfDay = hour;
  timeSlider.value = String(hour);
  timeValue.textContent = formatHourLabel(hour);
  updateAgentPositions();
  renderPieChart();
  renderScene();
}

function onWindowResize() {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderScene();
}

window.addEventListener("resize", onWindowResize);
controls.addEventListener("change", renderScene);
renderer.domElement.addEventListener("contextmenu", (event) => {
  event.preventDefault();
});
renderer.domElement.addEventListener("pointerdown", (event) => {
  pointerDownPosition = getCanvasRelativePointer(event);
});
renderer.domElement.addEventListener("pointerup", (event) => {
  if (!pointerDownPosition) {
    return;
  }

  const pointerUpPosition = getCanvasRelativePointer(event);
  const deltaX = pointerUpPosition.x - pointerDownPosition.x;
  const deltaY = pointerUpPosition.y - pointerDownPosition.y;
  const moveDistance = Math.hypot(deltaX, deltaY);
  pointerDownPosition = null;

  if (moveDistance > 5) {
    return;
  }

  const quadrantKey = getClickedQuadrantKey(event);

  if (!quadrantKey) {
    return;
  }

  if (event.button === 0) {
    cycleQuadrantState(quadrantKey);
  }

  if (event.button === 2) {
    cycleQuadrantSecondaryState(quadrantKey);
  }
});

transparencySlider.addEventListener("input", (event) => {
  const nextOpacity = Number(event.target.value) / 100;
  updateBuildingTransparency(nextOpacity);
});

function syncTimeSlider(event) {
  updateTimeOfDay(Number(event.target.value));
}

timeSlider.addEventListener("input", syncTimeSlider);
timeSlider.addEventListener("change", syncTimeSlider);

updateBuildingTransparency(1);
updateTimeOfDay(0);
updateAgentPositions();
renderRadarChart();
renderPieChart();
renderScene();
