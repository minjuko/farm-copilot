import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { LoadingProvider } from '../../../LoadingContext';
import { getCropList } from '../../../apis/crop';
import CropSelectionPage from './CropSelectionPage';

jest.mock('../../../apis/crop', () => ({
  getCropList: jest.fn(),
  deleteCrop: jest.fn(),
  updateSessionName: jest.fn(),
}));
jest.mock('../../atoms/GlobalLoader', () => () => null);
jest.mock('../../atoms/ConfirmModal', () => () => null);

const renderPage = () => render(
  <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
    <LoadingProvider><CropSelectionPage /></LoadingProvider>
  </MemoryRouter>
);

beforeEach(() => jest.clearAllMocks());

test('shows loading, then a genuine empty history', async () => {
  let resolveRequest;
  getCropList.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve; }));
  renderPage();

  expect(screen.getByRole('status')).toHaveTextContent('이력을 불러오는 중입니다.');
  expect(screen.queryByText(/등록한 작물 조합이 존재하지 않습니다/)).not.toBeInTheDocument();
  resolveRequest({ data: [] });

  expect(await screen.findByText(/등록한 작물 조합이 존재하지 않습니다/)).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});

test('shows a load failure separately and retries to a successful empty history', async () => {
  getCropList.mockRejectedValueOnce({ response: { status: 503 } }).mockResolvedValueOnce({ data: [] });
  renderPage();

  expect(await screen.findByRole('alert')).toHaveTextContent('다시 시도해 주세요');
  expect(screen.queryByText(/등록한 작물 조합이 존재하지 않습니다/)).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '다시 시도' }));

  await waitFor(() => expect(getCropList).toHaveBeenCalledTimes(2));
  expect(await screen.findByText(/등록한 작물 조합이 존재하지 않습니다/)).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
