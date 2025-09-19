import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  LineChart,
  Line,
  Legend
} from 'recharts';
import { Card } from '@/components/ui/card';
import { Visualization, ChartData } from '@/lib/api';

interface ChartVisualizationProps {
  visualization: Visualization;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D', '#FFC658', '#FF7C7C'];

export const ChartVisualization: React.FC<ChartVisualizationProps> = ({ visualization }) => {
  const { chart_type, meta, data } = visualization;

  const renderHistogram = () => {
    const chartData = data.map((item, index) => ({
      name: `${item.bin_start?.toFixed(1)}-${item.bin_end?.toFixed(1)}`,
      value: item.count,
      bin_start: item.bin_start,
      bin_end: item.bin_end,
      count: item.count,
      pct: item.pct
    }));

    return (
      <ResponsiveContainer width="100%" height={400}>
        <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="name" 
            angle={-45}
            textAnchor="end"
            height={80}
            fontSize={12}
          />
          <YAxis 
            label={{ value: meta.y_label, angle: -90, position: 'insideLeft' }}
            fontSize={12}
          />
          <Tooltip 
            formatter={(value: any, name: string, props: any) => [
              `${value} (${(props.payload.pct * 100).toFixed(1)}%)`,
              'Количество'
            ]}
            labelFormatter={(label, payload) => {
              if (payload && payload[0]) {
                return `Диапазон: ${payload[0].payload.bin_start?.toFixed(1)} - ${payload[0].payload.bin_end?.toFixed(1)}`;
              }
              return label;
            }}
          />
          <Bar dataKey="value" fill="#0088FE" />
        </BarChart>
      </ResponsiveContainer>
    );
  };

  const renderPieChart = () => {
    const chartData = data.map((item, index) => ({
      name: item.name || `Категория ${index + 1}`,
      value: item.value || item.count || 0,
      fill: COLORS[index % COLORS.length]
    }));

    return (
      <ResponsiveContainer width="100%" height={400}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            outerRadius={120}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.fill} />
            ))}
          </Pie>
          <Tooltip formatter={(value: any) => [value, 'Значение']} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    );
  };

  const renderScatterPlot = () => {
    const chartData = data.map((item, index) => ({
      x: item.x || item[meta.x_label] || index,
      y: item.y || item[meta.y_label] || item.value || 0,
      name: item.name || `Точка ${index + 1}`
    }));

    return (
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart 
          data={chartData}
          margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
        >
          <CartesianGrid />
          <XAxis 
            type="number" 
            dataKey="x" 
            name={meta.x_label}
            label={{ value: meta.x_label, position: 'insideBottom', offset: -10 }}
            domain={['dataMin', 'dataMax']}
          />
          <YAxis 
            type="number" 
            dataKey="y" 
            name={meta.y_label}
            label={{ value: meta.y_label, angle: -90, position: 'insideLeft' }}
            domain={['dataMin', 'dataMax']}
            scale="linear"
            tickFormatter={(value) => {
              if (value >= 1000000) {
                return `${(value / 1000000).toFixed(1)}M`;
              } else if (value >= 1000) {
                return `${(value / 1000).toFixed(0)}K`;
              }
              return value.toString();
            }}
          />
          <Tooltip 
            cursor={{ strokeDasharray: '3 3' }}
            formatter={(value: any, name: string, props: any) => {
              if (name === 'y') {
                return [typeof value === 'number' ? value.toLocaleString('ru-RU') : value, meta.y_label];
              }
              return [value, meta.x_label];
            }}
            labelFormatter={(label, payload) => {
              if (payload && payload[0]) {
                return `${meta.x_label}: ${payload[0].payload.x}, ${meta.y_label}: ${payload[0].payload.y?.toLocaleString('ru-RU')}`;
              }
              return label;
            }}
          />
          <Scatter dataKey="y" fill="#8884d8" />
        </ScatterChart>
      </ResponsiveContainer>
    );
  };

  const renderLineChart = () => {
    const chartData = data.map((item, index) => {
      let xValue = item.x || index;
      
      // Если x содержит временную метку, обрезаем временную зону
      if (typeof xValue === 'string' && (xValue.includes('T') || xValue.includes('Z') || xValue.includes('+'))) {
        // Обрезаем временную зону (все после 'T' или 'Z' или '+')
        xValue = xValue.split('T')[0].split('Z')[0].split('+')[0];
      }
      
      return {
        name: item.name || item.label || `Точка ${index + 1}`,
        value: item.value || item.y || 0,
        x: xValue,
        originalX: item.x || index
      };
    });

    return (
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="x" 
            label={{ value: meta.x_label, position: 'insideBottom', offset: -10 }}
            angle={-45}
            textAnchor="end"
            height={80}
            fontSize={12}
          />
          <YAxis 
            label={{ value: meta.y_label, angle: -90, position: 'insideLeft' }}
          />
          <Tooltip 
            formatter={(value: any, name: string, props: any) => [
              typeof value === 'number' ? value.toLocaleString('ru-RU') : value,
              meta.y_label
            ]}
            labelFormatter={(label, payload) => {
              if (payload && payload[0]) {
                return `${meta.x_label}: ${payload[0].payload.x}`;
              }
              return label;
            }}
          />
          <Legend />
          <Line 
            type="monotone" 
            dataKey="value" 
            stroke="#8884d8" 
            strokeWidth={2}
            dot={{ fill: '#8884d8', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    );
  };

  const renderChart = () => {
    switch (chart_type) {
      case 'histogram':
        return renderHistogram();
      case 'pie':
        return renderPieChart();
      case 'scatter':
        return renderScatterPlot();
      case 'line':
        return renderLineChart();
      case 'error':
        return (
          <div className="text-center text-red-500 py-8">
            <div className="text-lg font-semibold mb-2">Ошибка создания графика</div>
          </div>
        );
      default:
        return <div className="text-center text-muted-foreground">Неподдерживаемый тип графика: {chart_type}</div>;
    }
  };

  return (
    <Card className="p-4 mt-4">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-lg font-semibold">{meta.title}</h4>
          <span className="text-sm text-muted-foreground bg-muted px-2 py-1 rounded">
            {chart_type.toUpperCase()}
          </span>
        </div>
        <div className="w-full">
          {renderChart()}
        </div>
      </div>
    </Card>
  );
};
