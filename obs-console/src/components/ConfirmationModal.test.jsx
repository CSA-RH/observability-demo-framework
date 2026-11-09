import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConfirmationModal from './ConfirmationModal';

describe('ConfirmationModal', () => {
    beforeEach(() => {
        document.body.innerHTML = '<div id="modal-root"></div>';
    });

    it('renders nothing when hidden', () => {
        render(<ConfirmationModal show={false} title="Delete?" body="Sure?" />);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('shows title/body and wires the buttons', async () => {
        const onHide = vi.fn();
        const onConfirm = vi.fn();
        render(
            <ConfirmationModal show title="Delete user" body="This cannot be undone" confirmText="Delete"
                onHide={onHide} onConfirm={onConfirm} />,
        );

        expect(screen.getByRole('dialog')).toHaveTextContent('Delete user');
        expect(screen.getByText('This cannot be undone')).toBeInTheDocument();

        await userEvent.click(screen.getByRole('button', { name: 'Delete' }));
        await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
        await userEvent.click(screen.getByRole('button', { name: 'Close' }));
        expect(onConfirm).toHaveBeenCalledTimes(1);
        expect(onHide).toHaveBeenCalledTimes(2);
    });
});
