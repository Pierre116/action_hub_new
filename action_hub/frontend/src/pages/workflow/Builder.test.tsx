import { render } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import WorkflowBuilder from './WorkflowBuilder'

jest.mock('../../lib/api', () => ({
  __esModule: true,
  default: {
    get: jest.fn(async (url: string) => {
      if (url === '/api/teams') {
        return { data: { data: [] } }
      }
      if (url === '/api/topics') {
        return { data: { data: [] } }
      }
      if (url === '/api/workflow/templates') {
        return { data: [] }
      }
      return { data: { data: [] } }
    }),
    post: jest.fn(async () => ({ data: {} })),
  },
}))

jest.mock('@xyflow/react', () => {
  const React = require('react')
  return {
    ReactFlowProvider: ({ children }: any) => <div>{children}</div>,
    ReactFlow: ({ children }: any) => <div data-testid="reactflow">{children}</div>,
    Background: () => <div data-testid="background" />,
    Controls: () => <div data-testid="controls" />,
    MiniMap: () => <div data-testid="minimap" />,
    Handle: () => <span data-testid="handle" />,
    BackgroundVariant: { Dots: 'dots' },
    Position: { Left: 'left', Right: 'right' },
    MarkerType: { ArrowClosed: 'arrowclosed' },
    addEdge: (edge: any, edges: any[]) => [...edges, edge],
    useNodesState: (initial: any[] = []) => React.useState(initial),
    useEdgesState: (initial: any[] = []) => React.useState(initial),
  }
})

describe('WorkflowBuilder', () => {
  const renderWithQueryClient = (ui: React.ReactElement) => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    return render(
      <QueryClientProvider client={queryClient}>
        {ui}
      </QueryClientProvider>
    )
  }

  it('renders the builder page', () => {
    const { getByText } = renderWithQueryClient(<WorkflowBuilder />)
    expect(getByText('Workflow Builder')).toBeInTheDocument()
  });

  it('shows node palette with 8 node types', () => {
    const { getAllByText } = renderWithQueryClient(<WorkflowBuilder />)
    ;[
      'Task', 'Approval', 'Gateway', 'Service', 'Notification', 'Timer', 'Join', 'End'
    ].forEach(type => {
      expect(getAllByText(type).length).toBeGreaterThan(0)
    })
  });

  it('renders the canvas', () => {
    const { getByTestId } = renderWithQueryClient(<WorkflowBuilder />)
    expect(getByTestId('reactflow')).toBeInTheDocument()
    expect(getByTestId('background')).toBeInTheDocument()
    expect(getByTestId('controls')).toBeInTheDocument()
    expect(getByTestId('minimap')).toBeInTheDocument()
  })
})
