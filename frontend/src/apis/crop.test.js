import { instance } from './client';
import { deleteCrop, updateSessionName } from './crop';

jest.mock('./client', () => ({
  instance: {
    delete: jest.fn(),
    patch: jest.fn(),
  },
}));

beforeEach(() => jest.clearAllMocks());

test('deletes a prediction session with the backend DELETE contract', () => {
  deleteCrop('session-1');
  expect(instance.delete).toHaveBeenCalledWith('/prediction/delete_session/session-1/');
});

test('renames a prediction session with PATCH and session_name payload', () => {
  updateSessionName('session-1', '새 이름');
  expect(instance.patch).toHaveBeenCalledWith('/prediction/update_session_name/session-1/', {
    session_name: '새 이름',
  });
});
