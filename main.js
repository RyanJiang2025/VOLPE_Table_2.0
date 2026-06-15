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
let buildingOpacity = 1;

const transparencySlider = document.getElementById("transparency-slider");
const transparencyValue = document.getElementById("transparency-value");
const radarChart = document.getElementById("radar-chart");

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
  renderRadarChart();
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
  renderRadarChart();
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

function updateBuildingTransparency(value) {
  buildingOpacity = value;
  transparencyValue.textContent = `${Math.round(value * 100)}%`;
  Object.values(deployedQuadrants).forEach((quadrantGroup) => {
    applyBuildingOpacity(quadrantGroup);
  });
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

updateBuildingTransparency(1);
renderRadarChart();
renderScene();
