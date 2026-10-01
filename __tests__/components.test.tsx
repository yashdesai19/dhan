// Component library tests (React Native Testing Library, run by `npm test` under jest-expo).
import { fireEvent, render, screen } from '@testing-library/react-native';
import type { ReactElement } from 'react';

import {
  Banner,
  Button,
  EmptyState,
  IconButton,
  Keypad,
  Money,
  Pill,
  ProgressBar,
  SegmentedControl,
  TextField,
  Toggle,
} from '@/components';
import { ThemeProvider } from '@/theme';

const renderThemed = (ui: ReactElement, scheme: 'light' | 'dark' = 'light') =>
  render(<ThemeProvider forceScheme={scheme}>{ui}</ThemeProvider>);

describe('Money', () => {
  it('uses Indian grouping', () => {
    renderThemed(<Money amount={124580} />);
    expect(screen.getByText('₹1,24,580')).toBeTruthy();
  });
  it('renders the same value in dark mode', () => {
    renderThemed(<Money amount={24360} sign="plus" />, 'dark');
    expect(screen.getByText('+₹24,360')).toBeTruthy();
  });
});

describe('Button', () => {
  it('fires onPress and exposes its label', () => {
    const onPress = jest.fn();
    renderThemed(<Button label="Save expense" onPress={onPress} />);
    fireEvent.press(screen.getByRole('button', { name: 'Save expense' }));
    expect(onPress).toHaveBeenCalledTimes(1);
  });
  it('does not fire when disabled', () => {
    const onPress = jest.fn();
    renderThemed(<Button label="Save" onPress={onPress} disabled />);
    fireEvent.press(screen.getByRole('button', { name: 'Save' }));
    expect(onPress).not.toHaveBeenCalled();
  });
});

describe('IconButton', () => {
  it('is reachable by its accessibility label', () => {
    const onPress = jest.fn();
    renderThemed(<IconButton icon="bell" accessibilityLabel="Notifications" onPress={onPress} />);
    fireEvent.press(screen.getByLabelText('Notifications'));
    expect(onPress).toHaveBeenCalled();
  });
});

describe('Toggle', () => {
  it('is a switch that reports its state and flips', () => {
    const onChange = jest.fn();
    renderThemed(<Toggle value={false} onChange={onChange} accessibilityLabel="App lock" />);
    const sw = screen.getByRole('switch', { name: 'App lock' });
    expect(sw.props.accessibilityState).toMatchObject({ checked: false });
    fireEvent.press(sw);
    expect(onChange).toHaveBeenCalledWith(true);
  });
});

describe('SegmentedControl', () => {
  it('reports the chosen option', () => {
    const onChange = jest.fn();
    renderThemed(
      <SegmentedControl
        accessibilityLabel="Theme"
        value="system"
        onChange={onChange}
        options={[
          { value: 'system', label: 'System' },
          { value: 'light', label: 'Light' },
          { value: 'dark', label: 'Dark' },
        ]}
      />,
    );
    fireEvent.press(screen.getByText('Dark'));
    expect(onChange).toHaveBeenCalledWith('dark');
  });
});

describe('Keypad', () => {
  it('sends digits, decimal and delete', () => {
    const onKey = jest.fn();
    renderThemed(<Keypad onKey={onKey} />);
    fireEvent.press(screen.getByLabelText('4'));
    fireEvent.press(screen.getByLabelText('Decimal point'));
    fireEvent.press(screen.getByLabelText('Delete'));
    expect(onKey.mock.calls.map((c) => c[0])).toEqual(['4', '.', 'del']);
  });
});

describe('TextField', () => {
  it('renders label and receives typed input', () => {
    const onChange = jest.fn();
    renderThemed(<TextField label="Account name" value="HDFC" onChangeText={onChange} />);
    expect(screen.getByText('Account name')).toBeTruthy();
    fireEvent.changeText(screen.getByDisplayValue('HDFC'), 'SBI');
    expect(onChange).toHaveBeenCalledWith('SBI');
  });
});

describe('Pill', () => {
  it('renders label text', () => {
    renderThemed(<Pill label="On track" />);
    expect(screen.getByText('On track')).toBeTruthy();
  });
});

describe('ProgressBar', () => {
  it('renders progressbar accessibility element', () => {
    renderThemed(<ProgressBar value={60} accessibilityLabel="Goal progress" />);
    expect(screen.getByLabelText('Goal progress')).toBeTruthy();
  });
});

describe('EmptyState', () => {
  it('renders title and body', () => {
    renderThemed(<EmptyState icon="receipt" title="No transactions yet" body="Add one to see it here" />);
    expect(screen.getByText('No transactions yet')).toBeTruthy();
    expect(screen.getByText('Add one to see it here')).toBeTruthy();
  });
});

describe('Banner', () => {
  it('renders message content', () => {
    renderThemed(<Banner icon="info" tone="primary">Important notice</Banner>);
    expect(screen.getByText('Important notice')).toBeTruthy();
  });
});

