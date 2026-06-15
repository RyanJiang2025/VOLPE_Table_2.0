const TYPE_SQFT = {
  empty: 0,
  "public space": 625,
  podium: 2500,
  tower: 65000,
};

const METRIC_KEYS = [
  "usageDiversity",
  "economicVibrancy",
  "thirdSpaces",
  "housingAffordability",
  "emissionReduction",
];

const PRIMARY_USE_TYPES = ["public space", "podium", "tower"];
const SECONDARY_USE_TYPES = ["park", "plaza", "retail", "cafe", "office", "housing"];

const ECONOMIC_VIBRANCY_BASE = {
  cafe: 18,
  retail: 24,
  office: 22,
};

const THIRD_SPACES_BASE = {
  cafe: 14,
  park: 22,
  plaza: 18,
};

const HOUSING_AFFORDABILITY_BASE = {
  housing: 28,
};

const EMISSION_REDUCTION_BASE = {
  park: 16,
  housing: 14,
};

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function createEmptyMetricSet() {
  return {
    usageDiversity: 0,
    economicVibrancy: 0,
    thirdSpaces: 0,
    housingAffordability: 0,
    emissionReduction: 0,
  };
}

function createEmptyCountMap(keys) {
  return keys.reduce((counts, key) => {
    counts[key] = 0;
    return counts;
  }, {});
}

function withDefaultQuadrantShape(quadrant) {
  return {
    quadrantKey: quadrant.quadrantKey ?? "",
    primaryUse: quadrant.primaryUse ?? "empty",
    secondaryUse: quadrant.secondaryUse ?? "",
    squareFeet: quadrant.squareFeet ?? TYPE_SQFT[quadrant.primaryUse] ?? 0,
  };
}

function sumValues(values) {
  return values.reduce((total, value) => total + value, 0);
}

function calculateDiminishingReturnScore(countMap, baseScoreMap) {
  let total = 0;

  Object.entries(baseScoreMap).forEach(([useType, baseScore]) => {
    const count = countMap[useType] ?? 0;

    for (let index = 1; index <= count; index += 1) {
      total += baseScore / Math.sqrt(index);
    }
  });

  return total;
}

function calculateUsageDiversityScore(primaryCounts, secondaryCounts) {
  const activePrimaryCount = PRIMARY_USE_TYPES.filter((type) => primaryCounts[type] > 0).length;
  const activeSecondaryCount = SECONDARY_USE_TYPES.filter(
    (type) => secondaryCounts[type] > 0
  ).length;

  const primaryCoverage = activePrimaryCount / PRIMARY_USE_TYPES.length;
  const secondaryCoverage = activeSecondaryCount / SECONDARY_USE_TYPES.length;

  const evenlyDistributedPrimaryCount = PRIMARY_USE_TYPES.filter(
    (type) => primaryCounts[type] === 1
  ).length;
  const primaryBalance = evenlyDistributedPrimaryCount / PRIMARY_USE_TYPES.length;

  return clamp(
    primaryCoverage * 40 + secondaryCoverage * 45 + primaryBalance * 15,
    0,
    100
  );
}

function countUses(quadrants) {
  const primaryCounts = createEmptyCountMap(["empty", ...PRIMARY_USE_TYPES]);
  const secondaryCounts = createEmptyCountMap(SECONDARY_USE_TYPES);

  quadrants.forEach((quadrant) => {
    const primaryUse = quadrant.primaryUse;
    const secondaryUse = quadrant.secondaryUse;

    if (primaryUse in primaryCounts) {
      primaryCounts[primaryUse] += 1;
    }

    if (secondaryUse in secondaryCounts) {
      secondaryCounts[secondaryUse] += 1;
    }
  });

  return { primaryCounts, secondaryCounts };
}

function calculateNormalizedMetrics(rawMetrics) {
  return {
    usageDiversity: Math.round(clamp(rawMetrics.usageDiversity, 0, 100)),
    economicVibrancy: Math.round(clamp(rawMetrics.economicVibrancy, 0, 100)),
    thirdSpaces: Math.round(clamp(rawMetrics.thirdSpaces, 0, 100)),
    housingAffordability: Math.round(clamp(rawMetrics.housingAffordability, 0, 100)),
    emissionReduction: Math.round(clamp(rawMetrics.emissionReduction, 0, 100)),
  };
}

function calculateMetricBreakdown(quadrants, primaryCounts, secondaryCounts) {
  return {
    totalQuadrants: quadrants.length,
    primaryCounts,
    secondaryCounts,
    usageDiversity: {
      uniquePrimaryUses: PRIMARY_USE_TYPES.filter((type) => primaryCounts[type] > 0),
      uniqueSecondaryUses: SECONDARY_USE_TYPES.filter((type) => secondaryCounts[type] > 0),
    },
    economicVibrancy: {
      contributors: ["cafe", "retail", "office"],
      counts: {
        cafe: secondaryCounts.cafe,
        retail: secondaryCounts.retail,
        office: secondaryCounts.office,
      },
    },
    thirdSpaces: {
      contributors: ["cafe", "park", "plaza"],
      counts: {
        cafe: secondaryCounts.cafe,
        park: secondaryCounts.park,
        plaza: secondaryCounts.plaza,
      },
    },
    housingAffordability: {
      contributors: ["housing"],
      counts: {
        housing: secondaryCounts.housing,
      },
    },
    emissionReduction: {
      contributors: ["park", "housing"],
      counts: {
        park: secondaryCounts.park,
        housing: secondaryCounts.housing,
      },
    },
  };
}

export function calculateCommunityMetrics(quadrants) {
  const normalizedQuadrants = quadrants.map(withDefaultQuadrantShape);
  const { primaryCounts, secondaryCounts } = countUses(normalizedQuadrants);

  const rawMetrics = createEmptyMetricSet();
  rawMetrics.usageDiversity = calculateUsageDiversityScore(primaryCounts, secondaryCounts);
  rawMetrics.economicVibrancy = calculateDiminishingReturnScore(
    secondaryCounts,
    ECONOMIC_VIBRANCY_BASE
  );
  rawMetrics.thirdSpaces = calculateDiminishingReturnScore(
    secondaryCounts,
    THIRD_SPACES_BASE
  );
  rawMetrics.housingAffordability = calculateDiminishingReturnScore(
    secondaryCounts,
    HOUSING_AFFORDABILITY_BASE
  );
  rawMetrics.emissionReduction = calculateDiminishingReturnScore(
    secondaryCounts,
    EMISSION_REDUCTION_BASE
  );

  const normalizedMetrics = calculateNormalizedMetrics(rawMetrics);
  const totalSquareFeet = sumValues(normalizedQuadrants.map((quadrant) => quadrant.squareFeet));
  const breakdown = calculateMetricBreakdown(
    normalizedQuadrants,
    primaryCounts,
    secondaryCounts
  );

  return {
    rawMetrics,
    normalizedMetrics,
    totalSquareFeet,
    quadrants: normalizedQuadrants,
    breakdown,
  };
}

export function quadrantStatesToCommunityInput(primaryStates, secondaryStates) {
  return Object.keys(primaryStates).map((quadrantKey) => ({
    quadrantKey,
    primaryUse: primaryStates[quadrantKey] ?? "empty",
    secondaryUse: secondaryStates[quadrantKey] ?? "",
    squareFeet: TYPE_SQFT[primaryStates[quadrantKey]] ?? 0,
  }));
}

export function calculateCommunityMetricsFromStates(primaryStates, secondaryStates) {
  const quadrants = quadrantStatesToCommunityInput(primaryStates, secondaryStates);
  return calculateCommunityMetrics(quadrants);
}

export {
  ECONOMIC_VIBRANCY_BASE,
  EMISSION_REDUCTION_BASE,
  HOUSING_AFFORDABILITY_BASE,
  METRIC_KEYS,
  PRIMARY_USE_TYPES,
  SECONDARY_USE_TYPES,
  THIRD_SPACES_BASE,
  TYPE_SQFT,
};
