import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import StartWorkflow from './StartWorkflow';

// Mock axios
jest.mock('axios', () => ({
  get: jest.fn(() => Promise.resolve({ data: { data: [
    { wft_id: 1, wft_name_en: 'Test Template' }
  ] } })),
  post: jest.fn(() => Promise.resolve({ data: { instance_id: 123 } })),
}));

describe('StartWorkflow', () => {
  function renderPage() {
    const queryClient = new QueryClient();
    render(
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <StartWorkflow />
        </BrowserRouter>
      </QueryClientProvider>
    );
  }

    it('renders form and submits successfully', async () => {
      await act(async () => {
        renderPage();
      });
      const select = await screen.findByLabelText(/Workflow Template/i);
      await act(async () => {
        await waitFor(() => {
          expect(select.querySelector('option[value="1"]')).toBeTruthy();
        }, { timeout: 2000 });
      });
      fireEvent.change(select, { target: { value: '1' } });
      fireEvent.change(screen.getByLabelText(/Title/i), { target: { value: 'My Workflow' } });
      const submitBtn = await screen.findByRole('button', { name: /Start Workflow/i });
      fireEvent.click(submitBtn);
      await waitFor(() => {
        // Should navigate (mocked), so no error
        expect(screen.queryByRole('alert')).not.toBeInTheDocument();
      });
  });

  it('shows error if required fields missing', async () => {
    renderPage();
    const submitBtn = await screen.findByRole('button', { name: /Start Workflow/i });
    fireEvent.click(submitBtn);
    expect(await screen.findByText(/required/i)).toBeInTheDocument();
  });
});
