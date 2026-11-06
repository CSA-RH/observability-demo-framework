import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PasswordCell from './PasswordCell';

const renderCell = () => render(<table><tbody><tr><PasswordCell password="s3cret" /></tr></tbody></table>);

describe('PasswordCell', () => {
    it('masks the password until toggled', async () => {
        renderCell();
        expect(screen.queryByText('s3cret')).not.toBeInTheDocument();

        await userEvent.click(screen.getByTitle('Show Password'));
        expect(screen.getByText('s3cret')).toBeInTheDocument();

        await userEvent.click(screen.getByTitle('Hide Password'));
        expect(screen.queryByText('s3cret')).not.toBeInTheDocument();
    });

    it('copies the password to the clipboard', async () => {
        const user = userEvent.setup();
        renderCell();
        await user.click(screen.getByTitle('Copy to Clipboard'));
        expect(await navigator.clipboard.readText()).toBe('s3cret');
        expect(screen.getByTitle('Copied!')).toBeInTheDocument();
    });
});
