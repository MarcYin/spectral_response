(function () {
  const PAGE_ID = "rsrf-visualization-page";
  const PALETTE = [
    "#0f766e",
    "#c7771a",
    "#2563eb",
    "#be185d",
    "#4d7c0f",
    "#7c3aed",
    "#b45309",
    "#0f172a",
    "#0891b2",
    "#dc2626",
    "#6d28d9",
    "#15803d",
  ];

  document.addEventListener("DOMContentLoaded", () => {
    const page = document.getElementById(PAGE_ID);
    if (!page) {
      return;
    }
    document.body.classList.add("rsrf-viz-layout");
    const article = page.closest(".md-content__inner");
    if (article) {
      article.classList.add("rsrf-viz-article");
    }
    initVisualizations(page).catch((error) => {
      console.error(error);
      page.insertAdjacentHTML(
        "beforeend",
        `<div class="rsrf-viz-panel rsrf-viz-empty">Failed to load visualization assets: ${escapeHtml(
          String(error.message || error),
        )}</div>`,
      );
    });
  });

  async function initVisualizations(page) {
    if (!window.Plotly) {
      throw new Error("Plotly failed to load");
    }

    const indexUrl = resolveAssetUrl(page.dataset.indexPath);
    const overlapUrl = resolveAssetUrl(page.dataset.overlapPath);
    const [indexData, overlapData] = await Promise.all([
      loadJson(indexUrl),
      loadJson(overlapUrl),
    ]);

    const sensorCache = new Map();
    const sensorSummaries = new Map(indexData.sensors.map((sensor) => [sensor.sensor_key, sensor]));
    const overlapSummaries = new Map(overlapData.sensors.map((sensor) => [sensor.sensor_key, sensor]));
    const state = {
      activeSensorKey: indexData.sensors[0] ? indexData.sensors[0].sensor_key : null,
      selectedBandIds: new Set(),
      bandFilter: "",
      selectedWavelength: 865,
      overlapRequest: 0,
    };

    const explorer = {
      sensorSelect: document.getElementById("rsrf-explorer-sensor"),
      bandFilter: document.getElementById("rsrf-explorer-band-filter"),
      bandMeta: document.getElementById("rsrf-explorer-band-meta"),
      bandList: document.getElementById("rsrf-explorer-band-list"),
      featuredButton: document.getElementById("rsrf-explorer-featured"),
      allButton: document.getElementById("rsrf-explorer-all"),
      clearButton: document.getElementById("rsrf-explorer-clear"),
      stats: document.getElementById("rsrf-explorer-stats"),
      plot: document.getElementById("rsrf-explorer-plot"),
    };

    const overlap = {
      slider: document.getElementById("rsrf-overlap-slider"),
      wavelengthChip: document.getElementById("rsrf-overlap-wavelength"),
      heatmap: document.getElementById("rsrf-overlap-heatmap"),
      stats: document.getElementById("rsrf-overlap-stats"),
      bars: document.getElementById("rsrf-overlap-bars"),
      tableBody: document.getElementById("rsrf-overlap-table-body"),
    };

    if (overlap.slider) {
      overlap.slider.value = String(state.selectedWavelength);
    }

    populateSensorSelect(explorer.sensorSelect, indexData.sensors);
    explorer.sensorSelect.value = state.activeSensorKey || "";

    explorer.sensorSelect.addEventListener("change", async () => {
      state.activeSensorKey = explorer.sensorSelect.value;
      state.selectedBandIds.clear();
      state.bandFilter = "";
      explorer.bandFilter.value = "";
      await renderExplorer(indexUrl, sensorSummaries, sensorCache, state, explorer);
    });

    explorer.bandFilter.addEventListener("input", async () => {
      state.bandFilter = explorer.bandFilter.value.trim().toLowerCase();
      await renderExplorer(indexUrl, sensorSummaries, sensorCache, state, explorer);
    });

    explorer.featuredButton.addEventListener("click", async () => {
      const detail = await loadSensorDetail(
        sensorSummaries.get(state.activeSensorKey),
        sensorCache,
        indexUrl,
      );
      state.selectedBandIds = new Set(defaultFeaturedBandIds(detail));
      await renderExplorer(indexUrl, sensorSummaries, sensorCache, state, explorer, detail);
    });

    explorer.allButton.addEventListener("click", async () => {
      const detail = await loadSensorDetail(
        sensorSummaries.get(state.activeSensorKey),
        sensorCache,
        indexUrl,
      );
      state.selectedBandIds = new Set(detail.bands.map((band) => band.band_id));
      await renderExplorer(indexUrl, sensorSummaries, sensorCache, state, explorer, detail);
    });

    explorer.clearButton.addEventListener("click", async () => {
      state.selectedBandIds.clear();
      await renderExplorer(indexUrl, sensorSummaries, sensorCache, state, explorer);
    });

    overlap.slider.addEventListener("input", async () => {
      state.selectedWavelength = Number(overlap.slider.value);
      await renderOverlap(indexUrl, indexData, overlapSummaries, sensorCache, state, overlap);
    });

    await renderExplorer(indexUrl, sensorSummaries, sensorCache, state, explorer);
    await renderHeatmap(indexUrl, indexData, overlapSummaries, sensorCache, overlap, state);
    await renderOverlap(indexUrl, indexData, overlapSummaries, sensorCache, state, overlap);
  }

  function populateSensorSelect(selectElement, sensors) {
    selectElement.innerHTML = "";
    sensors.forEach((sensor) => {
      const option = document.createElement("option");
      option.value = sensor.sensor_key;
      option.textContent = sensor.label;
      selectElement.appendChild(option);
    });
  }

  async function renderExplorer(indexUrl, sensorSummaries, sensorCache, state, explorer, detailOverride) {
    const sensorSummary = sensorSummaries.get(state.activeSensorKey);
    if (!sensorSummary) {
      explorer.stats.innerHTML = '<div class="rsrf-viz-empty">No sensor representations available.</div>';
      explorer.bandMeta.textContent = "No sensor selected";
      explorer.bandList.innerHTML = "";
      Plotly.purge(explorer.plot);
      return;
    }

    const detail = detailOverride || (await loadSensorDetail(sensorSummary, sensorCache, indexUrl));
    if (state.selectedBandIds.size === 0) {
      state.selectedBandIds = new Set(defaultFeaturedBandIds(detail));
    }

    renderExplorerStats(detail, explorer.stats, state.selectedBandIds.size);
    renderBandList(detail, state, explorer);
    renderExplorerPlot(detail, explorer.plot, state.selectedBandIds);
  }

  function renderExplorerStats(detail, statsElement, selectedCount) {
    const stats = [
      ["Sensor", detail.label],
      ["Curve source", detail.curve_origin.replaceAll("_", " ")],
      ["Band count", `${selectedCount} selected / ${detail.band_count}`],
      [
        "Span",
        `${formatNumber(detail.wavelength_min_nm, 0)} to ${formatNumber(detail.wavelength_max_nm, 0)} nm`,
      ],
    ];
    statsElement.innerHTML = stats
      .map(
        ([label, value]) => `
          <div class="rsrf-viz-stat">
            <div class="rsrf-viz-stat-label">${escapeHtml(label)}</div>
            <div class="rsrf-viz-stat-value">${escapeHtml(value)}</div>
          </div>
        `,
      )
      .join("");
  }

  function renderBandList(detail, state, explorer) {
    const visibleBands = detail.bands.filter((band) => {
      if (!state.bandFilter) {
        return true;
      }
      const haystack = `${band.band_id} ${band.band_name}`.toLowerCase();
      return haystack.includes(state.bandFilter);
    });

    explorer.bandMeta.textContent = `${state.selectedBandIds.size} selected of ${detail.band_count} bands`;
    explorer.bandList.innerHTML = "";

    visibleBands.forEach((band, index) => {
      const row = document.createElement("label");
      row.className = "rsrf-viz-band-row";
      row.style.setProperty("--band-color", colorForIndex(index));

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = state.selectedBandIds.has(band.band_id);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          state.selectedBandIds.add(band.band_id);
        } else {
          state.selectedBandIds.delete(band.band_id);
        }
        renderExplorerStats(detail, explorer.stats, state.selectedBandIds.size);
        renderExplorerPlot(detail, explorer.plot, state.selectedBandIds);
        explorer.bandMeta.textContent = `${state.selectedBandIds.size} selected of ${detail.band_count} bands`;
      });

      const content = document.createElement("div");
      content.innerHTML = `
        <div class="rsrf-viz-band-title">${escapeHtml(band.band_id)}${band.band_name && band.band_name !== band.band_id ? ` · ${escapeHtml(band.band_name)}` : ""}</div>
        <div class="rsrf-viz-band-subtitle">
          ${formatBandSubtitle(band)}
        </div>
      `;

      row.appendChild(checkbox);
      row.appendChild(content);
      explorer.bandList.appendChild(row);
    });

    if (visibleBands.length === 0) {
      explorer.bandList.innerHTML = '<div class="rsrf-viz-empty">No bands match the current filter.</div>';
    }
  }

  function renderExplorerPlot(detail, plotElement, selectedBandIds) {
    const selectedBands = detail.bands.filter((band) => selectedBandIds.has(band.band_id));
    if (selectedBands.length === 0) {
      Plotly.react(
        plotElement,
        [],
        {
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          margin: { l: 54, r: 20, t: 30, b: 52 },
          annotations: [
            {
              text: "Choose at least one band to display.",
              showarrow: false,
              font: { size: 16, color: "#5f6c76" },
            },
          ],
          xaxis: { visible: false },
          yaxis: { visible: false },
        },
        plotConfig(),
      );
      return;
    }

    const traces = selectedBands.map((band, index) => ({
      type: "scatter",
      mode: "lines",
      name: band.band_name && band.band_name !== band.band_id ? `${band.band_id} · ${band.band_name}` : band.band_id,
      x: band.points.map((point) => point[0]),
      y: band.points.map((point) => point[1]),
      line: {
        width: 2.4,
        color: colorForIndex(index),
      },
      hovertemplate:
        `<b>${escapeHtml(band.band_id)}</b><br>` +
        `${band.band_name ? `${escapeHtml(band.band_name)}<br>` : ""}` +
        "Wavelength: %{x:.1f} nm<br>" +
        "Response: %{y:.3f}<extra></extra>",
    }));

    const xMin = Math.min(...selectedBands.map((band) => band.support_min_nm));
    const xMax = Math.max(...selectedBands.map((band) => band.support_max_nm));
    const xPadding = Math.max(5, (xMax - xMin) * 0.05);
    const yMax = Math.max(
      1.0,
      ...selectedBands.map((band) => Math.max(...band.points.map((point) => point[1]))),
    );

    Plotly.react(
      plotElement,
      traces,
      {
        margin: { l: 62, r: 24, t: 24, b: 56 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        hovermode: "x unified",
        legend: {
          orientation: "h",
          y: 1.14,
          x: 0,
        },
        xaxis: {
          title: "Wavelength (nm)",
          range: [xMin - xPadding, xMax + xPadding],
          gridcolor: "rgba(91, 84, 72, 0.1)",
          zeroline: false,
        },
        yaxis: {
          title: "Response",
          range: [0, Math.max(1.02, yMax * 1.08)],
          gridcolor: "rgba(91, 84, 72, 0.1)",
          zeroline: false,
        },
      },
      plotConfig(),
    );
  }

  async function renderHeatmap(indexUrl, indexData, overlapSummaries, sensorCache, overlap, state) {
    const sensors = indexData.sensors;
    const wavelengths = indexData.grid.wavelength_nm;
    const height = Math.max(720, sensors.length * 15 + 140);

    await Plotly.newPlot(
      overlap.heatmap,
      [
        {
          type: "heatmap",
          z: indexData.heatmap.z,
          x: wavelengths,
          y: sensors.map((sensor) => sensor.label),
          colorscale: [
            [0.0, "#fff7e6"],
            [0.2, "#f6c95f"],
            [0.5, "#ef8a3b"],
            [0.75, "#2a9d8f"],
            [1.0, "#16425b"],
          ],
          zmin: 0,
          zmax: 1,
          hovertemplate:
            "<b>%{y}</b><br>" +
            "Wavelength: %{x:.0f} nm<br>" +
            "Normalized weight: %{z:.3f}<extra></extra>",
          colorbar: {
            title: "Weight",
            thickness: 12,
          },
        },
      ],
      {
        margin: { l: 180, r: 28, t: 22, b: 56 },
        height,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        xaxis: {
          title: "Wavelength (nm)",
          gridcolor: "rgba(91, 84, 72, 0.06)",
        },
        yaxis: {
          automargin: true,
        },
        shapes: [verticalGuideShape(state.selectedWavelength)],
      },
    );

    overlap.heatmap.on("plotly_click", async (event) => {
      if (!event.points || !event.points.length) {
        return;
      }
      state.selectedWavelength = Math.round(Number(event.points[0].x));
      overlap.slider.value = String(state.selectedWavelength);
      await renderOverlap(
        indexUrl,
        indexData,
        overlapSummaries,
        sensorCache,
        state,
        overlap,
      );
    });
  }

  async function renderOverlap(indexUrl, indexData, overlapSummaries, sensorCache, state, overlap) {
    state.overlapRequest += 1;
    const requestId = state.overlapRequest;
    const wavelength = Number(state.selectedWavelength);
    overlap.wavelengthChip.textContent = `${formatNumber(wavelength, 0)} nm`;
    await Plotly.relayout(overlap.heatmap, { shapes: [verticalGuideShape(wavelength)] });

    const candidateSummaries = [];
    overlapSummaries.forEach((sensor) => {
      const matchingBands = sensor.bands.filter(
        (band) => wavelength >= band.support_min_nm && wavelength <= band.support_max_nm,
      );
      if (matchingBands.length) {
        candidateSummaries.push({ sensor, bands: matchingBands });
      }
    });

    if (candidateSummaries.length === 0) {
      renderOverlapStats(overlap.stats, wavelength, []);
      renderOverlapBars(overlap.bars, []);
      overlap.tableBody.innerHTML = '<tr><td colspan="5" class="rsrf-viz-empty">No overlapping responses at this wavelength.</td></tr>';
      return;
    }

    const detailEntries = await Promise.all(
      candidateSummaries.map(async ({ sensor }) => [
        sensor.sensor_key,
        await loadSensorDetail(sensor, sensorCache, indexUrl),
      ]),
    );
    if (requestId !== state.overlapRequest) {
      return;
    }

    const detailMap = new Map(detailEntries);
    const overlaps = [];
    candidateSummaries.forEach(({ sensor, bands }) => {
      const detail = detailMap.get(sensor.sensor_key);
      if (!detail) {
        return;
      }
      const detailBands = new Map(detail.bands.map((band) => [band.band_id, band]));
      bands.forEach((band) => {
        const detailBand = detailBands.get(band.band_id);
        if (!detailBand) {
          return;
        }
        const response = interpolateBandResponse(detailBand.points, wavelength);
        if (response <= 0) {
          return;
        }
        overlaps.push({
          sensorLabel: sensor.label,
          bandLabel:
            band.band_name && band.band_name !== band.band_id
              ? `${band.band_id} · ${band.band_name}`
              : band.band_id,
          response,
          support: `${formatNumber(band.support_min_nm, 0)} to ${formatNumber(band.support_max_nm, 0)} nm`,
          curveOrigin: band.curve_origin.replaceAll("_", " "),
        });
      });
    });

    overlaps.sort((left, right) => right.response - left.response || left.sensorLabel.localeCompare(right.sensorLabel));
    renderOverlapStats(overlap.stats, wavelength, overlaps);
    renderOverlapBars(overlap.bars, overlaps);
    renderOverlapTable(overlap.tableBody, overlaps);
  }

  function renderOverlapStats(statsElement, wavelength, overlaps) {
    const uniqueSensors = new Set(overlaps.map((item) => item.sensorLabel));
    const strongest = overlaps[0];
    const stats = [
      ["Wavelength", `${formatNumber(wavelength, 0)} nm`],
      ["Sensors", `${uniqueSensors.size}`],
      ["Bands", `${overlaps.length}`],
      ["Strongest overlap", strongest ? `${strongest.bandLabel}` : "None"],
    ];
    statsElement.innerHTML = stats
      .map(
        ([label, value]) => `
          <div class="rsrf-viz-stat">
            <div class="rsrf-viz-stat-label">${escapeHtml(label)}</div>
            <div class="rsrf-viz-stat-value">${escapeHtml(value)}</div>
          </div>
        `,
      )
      .join("");
  }

  function renderOverlapBars(plotElement, overlaps) {
    if (!overlaps.length) {
      Plotly.react(
        plotElement,
        [],
        {
          paper_bgcolor: "rgba(0,0,0,0)",
          plot_bgcolor: "rgba(0,0,0,0)",
          margin: { l: 54, r: 20, t: 30, b: 52 },
          annotations: [
            {
              text: "No overlaps at the selected wavelength.",
              showarrow: false,
              font: { size: 16, color: "#5f6c76" },
            },
          ],
          xaxis: { visible: false },
          yaxis: { visible: false },
        },
        plotConfig(),
      );
      return;
    }

    const top = overlaps.slice(0, 30).reverse();
    Plotly.react(
      plotElement,
      [
        {
          type: "bar",
          orientation: "h",
          x: top.map((item) => item.response),
          y: top.map((item) => `${item.bandLabel} · ${item.sensorLabel}`),
          marker: {
            color: top.map((_, index) => colorForIndex(index)),
          },
          hovertemplate:
            "<b>%{y}</b><br>" +
            "Response at wavelength: %{x:.3f}<extra></extra>",
        },
      ],
      {
        margin: { l: 280, r: 20, t: 24, b: 56 },
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        xaxis: {
          title: "Response at selected wavelength",
          range: [0, 1.02],
          gridcolor: "rgba(91, 84, 72, 0.1)",
        },
        yaxis: {
          automargin: true,
        },
      },
      plotConfig(),
    );
  }

  function renderOverlapTable(tableBody, overlaps) {
    if (!overlaps.length) {
      tableBody.innerHTML = '<tr><td colspan="5" class="rsrf-viz-empty">No overlaps at the selected wavelength.</td></tr>';
      return;
    }
    tableBody.innerHTML = overlaps
      .map(
        (item) => `
          <tr>
            <td><strong>${escapeHtml(item.sensorLabel)}</strong></td>
            <td>${escapeHtml(item.bandLabel)}</td>
            <td>${formatNumber(item.response, 3)}</td>
            <td>${escapeHtml(item.support)}</td>
            <td>${escapeHtml(item.curveOrigin)}</td>
          </tr>
        `,
      )
      .join("");
  }

  async function loadSensorDetail(sensorSummary, sensorCache, indexUrl) {
    if (!sensorSummary) {
      throw new Error("Missing sensor summary");
    }
    if (sensorCache.has(sensorSummary.sensor_key)) {
      return sensorCache.get(sensorSummary.sensor_key);
    }
    const sensorUrl = new URL(sensorSummary.sensor_file, indexUrl).toString();
    const payload = await loadJson(sensorUrl);
    sensorCache.set(sensorSummary.sensor_key, payload);
    return payload;
  }

  function defaultFeaturedBandIds(detail) {
    if (detail.band_count <= 12) {
      return detail.bands.map((band) => band.band_id);
    }
    const count = Math.min(12, detail.bands.length);
    const indices = new Set();
    for (let index = 0; index < count; index += 1) {
      indices.add(Math.round((index * (detail.bands.length - 1)) / (count - 1)));
    }
    return detail.bands
      .filter((_, index) => indices.has(index))
      .map((band) => band.band_id);
  }

  function interpolateBandResponse(points, wavelength) {
    if (!points.length) {
      return 0;
    }
    if (wavelength < points[0][0] || wavelength > points[points.length - 1][0]) {
      return 0;
    }
    for (let index = 1; index < points.length; index += 1) {
      const left = points[index - 1];
      const right = points[index];
      if (wavelength <= right[0]) {
        const span = right[0] - left[0];
        if (span <= 0) {
          return right[1];
        }
        const ratio = (wavelength - left[0]) / span;
        return left[1] + ratio * (right[1] - left[1]);
      }
    }
    return 0;
  }

  function formatBandSubtitle(band) {
    const parts = [];
    if (band.center_wavelength_nm !== null && band.center_wavelength_nm !== undefined) {
      parts.push(`center ${formatNumber(band.center_wavelength_nm, 1)} nm`);
    }
    if (band.fwhm_nm !== null && band.fwhm_nm !== undefined) {
      parts.push(`FWHM ${formatNumber(band.fwhm_nm, 1)} nm`);
    }
    parts.push(`support ${formatNumber(band.support_min_nm, 0)} to ${formatNumber(band.support_max_nm, 0)} nm`);
    return escapeHtml(parts.join(" · "));
  }

  function verticalGuideShape(wavelength) {
    return {
      type: "line",
      x0: wavelength,
      x1: wavelength,
      yref: "paper",
      y0: 0,
      y1: 1,
      line: {
        color: "#111827",
        width: 2,
        dash: "dot",
      },
    };
  }

  function colorForIndex(index) {
    return PALETTE[index % PALETTE.length];
  }

  function plotConfig() {
    return {
      displaylogo: false,
      responsive: true,
      modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    };
  }

  function formatNumber(value, fractionDigits) {
    return Number(value).toLocaleString(undefined, {
      maximumFractionDigits: fractionDigits,
      minimumFractionDigits: fractionDigits,
    });
  }

  async function loadJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to load ${url}: ${response.status}`);
    }
    return response.json();
  }

  function resolveAssetUrl(relativePath) {
    return new URL(relativePath, window.location.href).toString();
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
})();
