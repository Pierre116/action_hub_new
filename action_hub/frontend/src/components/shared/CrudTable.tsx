import { useState, useMemo } from 'react'
import { Table, Pagination, Form, InputGroup, Button, Spinner } from 'react-bootstrap'
import { t } from '../../lib/i18n'
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
  ColumnDef,
  SortingState,
} from '@tanstack/react-table'

interface CrudTableProps<T> {
  data: T[]
  columns: ColumnDef<T, unknown>[]
  pageSize?: number
  searchPlaceholder?: string
  onRowClick?: (row: T) => void
  onAdd?: () => void
  onEdit?: (row: T) => void
  onDelete?: (row: T) => void
  isLoading?: boolean
  addButtonLabel?: string
}

export default function CrudTable<T>({
  data,
  columns,
  pageSize = 10,
  searchPlaceholder,
  onRowClick,
  onAdd,
  onEdit,
  onDelete,
  isLoading = false,
  addButtonLabel,
}: CrudTableProps<T>) {
  const [globalFilter, setGlobalFilter] = useState('')
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data,
    columns,
    state: {
      globalFilter,
      sorting,
    },
    onGlobalFilterChange: setGlobalFilter,
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    initialState: {
      pagination: {
        pageSize,
      },
    },
  })

  const renderActionsHeader = () => {
    if (!onEdit && !onDelete) return null
    return <th style={{ width: '120px' }}>{t('common.actions', 'Actions')}</th>
  }

  const renderActionsCell = (row: T) => {
    if (!onEdit && !onDelete) return null
    return (
      <td>
        {onEdit && (
          <Button
            variant="outline-primary"
            size="sm"
            className="me-1"
            onClick={(e) => {
              e.stopPropagation()
              onEdit(row)
            }}
          >
            {t('common.edit', 'Edit')}
          </Button>
        )}
        {onDelete && (
          <Button
            variant="outline-danger"
            size="sm"
            onClick={(e) => {
              e.stopPropagation()
              onDelete(row)
            }}
          >
            {t('common.delete', 'Delete')}
          </Button>
        )}
      </td>
    )
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        {searchPlaceholder && (
          <InputGroup style={{ maxWidth: '300px' }}>
            <Form.Control
              placeholder={searchPlaceholder}
              value={globalFilter ?? ''}
              onChange={(e) => setGlobalFilter(e.target.value)}
            />
          </InputGroup>
        )}
        {onAdd && (
          <Button variant="primary" onClick={onAdd}>
            {addButtonLabel || t('common.add', 'Add')}
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="text-center py-5">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
        </div>
      ) : (
        <Table hover responsive size="sm" className="mb-0" style={{ fontSize: '0.875rem' }}>
          <thead className="table-light">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    onClick={header.column.getToggleSortingHandler()}
                    style={{ cursor: header.column.getCanSort() ? 'pointer' : 'default' }}
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                    {{
                      asc: ' 🔼',
                      desc: ' 🔽',
                    }[header.column.getIsSorted() as string] ?? null}
                  </th>
                ))}
                {renderActionsHeader()}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 1} className="text-center text-muted py-4">
                  {t('common.noData', 'No data available')}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  onClick={() => onRowClick?.(row.original)}
                  style={{ cursor: onRowClick ? 'pointer' : 'default' }}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                  {renderActionsCell(row.original)}
                </tr>
              ))
            )}
          </tbody>
        </Table>
      )}

      <div className="d-flex justify-content-between align-items-center mt-3">
        <div>
          {t('table.pageInfo', 'Page {{page}} of {{pages}}', {
            page: table.getState().pagination.pageIndex + 1,
            pages: table.getPageCount(),
          })}
        </div>
        <Pagination>
          <Pagination.First
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
          />
          <Pagination.Prev
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          />
          <Pagination.Next
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          />
          <Pagination.Last
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
          />
        </Pagination>
      </div>
    </div>
  )
}
