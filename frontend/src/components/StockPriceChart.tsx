import React, { useEffect, useId, useState } from "react";

export interface StockChartPoint {
  date: string;
  close: number;
}

export interface StockChartData {
  available?: boolean;
  chart_type?: string;
  metric?: string;
  symbol: string;
  start_date?: string | null;
  end_date?: string | null;
  latest_close?: number | null;
  period_return_pct?: number | null;
  highest_high?: number | null;
  lowest_low?: number | null;
  average_volume?: number | null;
  observations?: number | null;
  sampled?: boolean;
  points: StockChartPoint[];
}

interface StockPriceChartProps {
  chart: StockChartData;
}

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const compactNumberFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const formatCurrency = (value: number | null | undefined) =>
  typeof value === "number" ? currencyFormatter.format(value) : "N/A";

const formatPercent = (value: number | null | undefined) =>
  typeof value === "number"
    ? `${value > 0 ? "+" : ""}${value.toFixed(2)}%`
    : "N/A";

const formatDate = (value: string | null | undefined) => {
  if (!value) {
    return "Unknown date";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

const StockPriceChart: React.FC<StockPriceChartProps> = ({ chart }) => {
  const points = chart.points ?? [];
  const [activeIndex, setActiveIndex] = useState(points.length - 1);
  const gradientId = useId();
  const width = 720;
  const height = 320;
  const padding = { top: 26, right: 26, bottom: 44, left: 58 };

  useEffect(() => {
    setActiveIndex(points.length - 1);
  }, [points.length, chart.symbol]);

  if (!chart.available || points.length < 2) {
    return null;
  }

  const closes = points.map((point) => point.close);
  const minClose = Math.min(...closes);
  const maxClose = Math.max(...closes);
  const priceSpan = Math.max(maxClose - minClose, maxClose * 0.04, 1);
  const yMin = minClose - priceSpan * 0.1;
  const yMax = maxClose + priceSpan * 0.1;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const safeActiveIndex = Math.min(
    Math.max(activeIndex, 0),
    points.length - 1,
  );
  const activePoint = points[safeActiveIndex];

  const xForIndex = (index: number) =>
    padding.left + (plotWidth * index) / Math.max(points.length - 1, 1);
  const yForValue = (value: number) =>
    padding.top + ((yMax - value) / (yMax - yMin)) * plotHeight;

  const linePath = points
    .map((point, index) => {
      const command = index === 0 ? "M" : "L";
      return `${command} ${xForIndex(index)} ${yForValue(point.close)}`;
    })
    .join(" ");

  const areaPath = [
    linePath,
    `L ${xForIndex(points.length - 1)} ${padding.top + plotHeight}`,
    `L ${xForIndex(0)} ${padding.top + plotHeight}`,
    "Z",
  ].join(" ");

  const yTicks = Array.from({ length: 4 }, (_, index) => {
    const ratio = index / 3;
    const value = yMax - (yMax - yMin) * ratio;
    return {
      value,
      y: padding.top + plotHeight * ratio,
    };
  });

  const xTicks = [
    { label: formatDate(points[0]?.date), x: xForIndex(0) },
    {
      label: formatDate(points[Math.floor((points.length - 1) / 2)]?.date),
      x: xForIndex(Math.floor((points.length - 1) / 2)),
    },
    {
      label: formatDate(points[points.length - 1]?.date),
      x: xForIndex(points.length - 1),
    },
  ];

  const handlePointerMove = (
    event:
      | React.MouseEvent<SVGRectElement>
      | React.TouchEvent<SVGRectElement>,
  ) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const clientX =
      "touches" in event ? event.touches[0]?.clientX ?? rect.left : event.clientX;
    const relativeX = Math.min(Math.max(clientX - rect.left, 0), rect.width);
    const ratio = rect.width > 0 ? relativeX / rect.width : 0;
    setActiveIndex(Math.round(ratio * (points.length - 1)));
  };

  const returnTone =
    typeof chart.period_return_pct === "number"
      ? chart.period_return_pct >= 0
        ? "positive"
        : "negative"
      : "neutral";

  return (
    <section className="stock-chart-card">
      <div className="stock-chart-header">
        <div>
          <p className="stock-chart-eyebrow">Interactive Chart</p>
          <h3>{chart.symbol} Closing Price</h3>
          <p className="stock-chart-subtitle">
            {formatDate(chart.start_date)} to {formatDate(chart.end_date)}
            {chart.sampled ? " • sampled for display" : ""}
          </p>
        </div>

        <div className={`stock-chart-return ${returnTone}`}>
          <span>Period change</span>
          <strong>{formatPercent(chart.period_return_pct)}</strong>
        </div>
      </div>

      <div className="stock-chart-metrics">
        <div className="stock-chart-metric">
          <span>Latest close</span>
          <strong>{formatCurrency(chart.latest_close)}</strong>
        </div>
        <div className="stock-chart-metric">
          <span>Range</span>
          <strong>
            {formatCurrency(chart.lowest_low)} to {formatCurrency(chart.highest_high)}
          </strong>
        </div>
        <div className="stock-chart-metric">
          <span>Average volume</span>
          <strong>
            {typeof chart.average_volume === "number"
              ? compactNumberFormatter.format(chart.average_volume)
              : "N/A"}
          </strong>
        </div>
      </div>

      <div className="stock-chart-stage">
        <div className="stock-chart-highlight">
          <span>{formatDate(activePoint.date)}</span>
          <strong>{formatCurrency(activePoint.close)}</strong>
        </div>

        <svg
          className="stock-chart-svg"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`${chart.symbol} closing price chart`}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(42, 198, 191, 0.38)" />
              <stop offset="100%" stopColor="rgba(42, 198, 191, 0.02)" />
            </linearGradient>
          </defs>

          {yTicks.map((tick) => (
            <g key={tick.y}>
              <line
                className="stock-chart-grid-line"
                x1={padding.left}
                x2={width - padding.right}
                y1={tick.y}
                y2={tick.y}
              />
              <text
                className="stock-chart-axis-label"
                x={padding.left - 12}
                y={tick.y + 4}
                textAnchor="end"
              >
                {currencyFormatter.format(tick.value)}
              </text>
            </g>
          ))}

          <path className="stock-chart-area" d={areaPath} fill={`url(#${gradientId})`} />
          <path className="stock-chart-line" d={linePath} />

          <line
            className="stock-chart-crosshair"
            x1={xForIndex(safeActiveIndex)}
            x2={xForIndex(safeActiveIndex)}
            y1={padding.top}
            y2={padding.top + plotHeight}
          />
          <circle
            className="stock-chart-point"
            cx={xForIndex(safeActiveIndex)}
            cy={yForValue(activePoint.close)}
            r="5"
          />

          {xTicks.map((tick) => (
            <text
              key={`${tick.label}-${tick.x}`}
              className="stock-chart-axis-label"
              x={tick.x}
              y={height - 14}
              textAnchor={
                tick.x === padding.left
                  ? "start"
                  : tick.x === width - padding.right
                    ? "end"
                    : "middle"
              }
            >
              {tick.label}
            </text>
          ))}

          <rect
            className="stock-chart-hit-area"
            x={padding.left}
            y={padding.top}
            width={plotWidth}
            height={plotHeight}
            onMouseMove={handlePointerMove}
            onMouseLeave={() => setActiveIndex(points.length - 1)}
            onTouchMove={handlePointerMove}
            onTouchStart={handlePointerMove}
          />
        </svg>
      </div>
    </section>
  );
};

export default StockPriceChart;
