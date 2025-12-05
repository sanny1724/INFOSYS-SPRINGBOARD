import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
    CategoryScale,
    LinearScale,
    BarElement,
    Title,
    Tooltip,
    Legend
);

export const options = {
    responsive: true,
    plugins: {
        legend: {
            position: 'top',
            labels: {
                color: 'white'
            }
        },
        title: {
            display: true,
            text: 'Detection Analytics (Last 24h)',
            color: 'white'
        },
    },
    scales: {
        y: {
            ticks: { color: 'white' },
            grid: { color: 'rgba(255,255,255,0.1)' }
        },
        x: {
            ticks: { color: 'white' },
            grid: { color: 'rgba(255,255,255,0.1)' }
        }
    }
};

const AnalyticsChart = ({ history }) => {

    const poacherCount = history.filter(h => parseFloat(h.poacher) > 0).length;
    const weaponCount = history.filter(h => parseFloat(h.weapon) > 0).length;
    const safeCount = history.filter(h => parseFloat(h.poacher) === 0 && parseFloat(h.weapon) === 0).length;

    const data = {
        labels: ['Poachers', 'Weapons', 'Safe Scans'],
        datasets: [
            {
                label: 'Detections',
                data: [poacherCount, weaponCount, safeCount],
                backgroundColor: ['rgba(255, 99, 132, 0.8)', 'rgba(255, 206, 86, 0.8)', 'rgba(75, 192, 192, 0.8)'],
            },
        ],
    };

    return <Bar options={options} data={data} />;
}

export default AnalyticsChart;
