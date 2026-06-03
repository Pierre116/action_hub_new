import { Card } from 'react-bootstrap'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData,
} from 'chart.js'
import { Chart, Line, Bar, Pie, Doughnut } from 'react-chartjs-2'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
)

interface ChartPanelProps {
  title: string
  type: 'line' | 'bar' | 'pie' | 'doughnut'
  data: ChartData<typeof type>
  options?: ChartOptions<typeof type>
  height?: number
}

export default function ChartPanel({
  title,
  type,
  data,
  options,
  height = 300,
}: ChartPanelProps) {
  const defaultOptions: ChartOptions<typeof type> = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'bottom' as const,
      },
    },
  }

  const mergedOptions = { ...defaultOptions, ...options }

  const renderChart = () => {
    switch (type) {
      case 'line':
        return <Line data={data} options={mergedOptions} />
      case 'bar':
        return <Bar data={data} options={mergedOptions} />
      case 'pie':
        return <Pie data={data} options={mergedOptions} />
      case 'doughnut':
        return <Doughnut data={data} options={mergedOptions} />
      default:
        return null
    }
  }

  return (
    <Card>
      <Card.Header>
        <Card.Title as="h6" className="mb-0">
          {title}
        </Card.Title>
      </Card.Header>
      <Card.Body style={{ height }}>
        {renderChart()}
      </Card.Body>
    </Card>
  )
}
