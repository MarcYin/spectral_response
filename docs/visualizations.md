---
hide:
  - toc
---

# Interactive Visualizations

<div id="rsrf-visualization-page" class="rsrf-viz-page" data-index-path="../assets/visualization/index.json" data-overlap-path="../assets/visualization/overlap_index.json">
  <section class="rsrf-viz-hero">
    <p class="rsrf-viz-kicker">Optical response atlas</p>
    <h2>Explore the repository the way instrument engineers think about it</h2>
    <p>
      This page exposes two interactive views: a sensor explorer for exact band-level response
      inspection, and a wavelength overlap atlas for scanning the full <strong>300 to 2500 nm</strong>
      optical domain. Sampled curves are shown directly, while metadata-only band specs are
      realized as Gaussian display curves for comparison.
    </p>
  </section>

  <section class="rsrf-viz-section">
    <div class="rsrf-viz-section-header">
      <div>
        <p class="rsrf-viz-eyebrow">1. Sensor explorer</p>
        <h3>Select one sensor and the bands you want to inspect</h3>
      </div>
      <p class="rsrf-viz-copy">
        The chart auto-zooms to the selected bands. For broad multispectral sensors that means a
        tight wavelength window; for hyperspectral families it expands to the selected band set.
      </p>
    </div>

    <div class="rsrf-viz-grid">
      <aside class="rsrf-viz-panel rsrf-viz-control-panel">
        <label class="rsrf-viz-field">
          <span>Sensor representation</span>
          <select id="rsrf-explorer-sensor"></select>
        </label>

        <div class="rsrf-viz-actions">
          <button type="button" id="rsrf-explorer-featured">Featured</button>
          <button type="button" id="rsrf-explorer-all">All</button>
          <button type="button" id="rsrf-explorer-clear">Clear</button>
        </div>

        <label class="rsrf-viz-field">
          <span>Filter bands</span>
          <input id="rsrf-explorer-band-filter" type="search" placeholder="Search by band id or name" />
        </label>

        <div class="rsrf-viz-band-meta" id="rsrf-explorer-band-meta">Loading sensor bands...</div>
        <div class="rsrf-viz-band-list" id="rsrf-explorer-band-list"></div>
      </aside>

      <div class="rsrf-viz-panel rsrf-viz-stage-panel">
        <div class="rsrf-viz-stat-grid" id="rsrf-explorer-stats"></div>
        <div class="rsrf-viz-chart" id="rsrf-explorer-plot"></div>
      </div>
    </div>
  </section>

  <section class="rsrf-viz-section">
    <div class="rsrf-viz-section-header">
      <div>
        <p class="rsrf-viz-eyebrow">2. Wavelength overlap atlas</p>
        <h3>Click a wavelength region and see every response that overlaps it</h3>
      </div>
      <p class="rsrf-viz-copy">
        The heatmap uses the maximum peak-normalized response per sensor on a `1 nm` grid from
        `300` to `2500 nm`. Click the heatmap or drag the wavelength slider to reveal overlapping
        bands with response above `0.01`, then add the ones you care about into a full-curve
        comparison.
      </p>
    </div>

    <div class="rsrf-viz-panel rsrf-viz-overlap-panel">
      <div class="rsrf-viz-slider-row">
        <label class="rsrf-viz-field rsrf-viz-slider-field">
          <span>Selected wavelength</span>
          <input id="rsrf-overlap-slider" type="range" min="300" max="2500" value="865" />
        </label>
        <div class="rsrf-viz-wavelength-chip" id="rsrf-overlap-wavelength">865 nm</div>
      </div>

      <div class="rsrf-viz-chart rsrf-viz-heatmap-chart" id="rsrf-overlap-heatmap"></div>
      <div class="rsrf-viz-stat-grid" id="rsrf-overlap-stats"></div>

      <div class="rsrf-viz-overlap-grid">
        <aside class="rsrf-viz-overlap-selector-shell">
          <div class="rsrf-viz-overlap-toolbar">
            <div class="rsrf-viz-band-meta" id="rsrf-overlap-meta">
              Loading overlapping responses...
            </div>
            <div class="rsrf-viz-actions">
              <button type="button" id="rsrf-overlap-top">Top</button>
              <button type="button" id="rsrf-overlap-all">All</button>
              <button type="button" id="rsrf-overlap-clear">Clear</button>
            </div>
          </div>
          <div class="rsrf-viz-band-list rsrf-viz-overlap-list" id="rsrf-overlap-selector-list"></div>
        </aside>

        <div class="rsrf-viz-overlap-stage">
          <div class="rsrf-viz-chart rsrf-viz-overlap-curve-chart" id="rsrf-overlap-curves"></div>
        </div>
      </div>

      <div class="rsrf-viz-table-shell">
        <table class="rsrf-viz-table">
          <thead>
            <tr>
              <th>Compare</th>
              <th>Sensor</th>
              <th>Band</th>
              <th>Response</th>
              <th>Support</th>
              <th>Curve source</th>
            </tr>
          </thead>
          <tbody id="rsrf-overlap-table-body"></tbody>
        </table>
      </div>
    </div>
  </section>
</div>
