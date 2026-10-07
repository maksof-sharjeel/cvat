// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

import './styles.scss';

import React, { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router';
import { Bar } from 'react-chartjs-2';
import {
    Chart, BarElement, CategoryScale, LinearScale, Tooltip,
} from 'chart.js';
import Button from 'antd/lib/button';
import Empty from 'antd/lib/empty';
import Radio from 'antd/lib/radio';
import Result from 'antd/lib/result';
import Text from 'antd/lib/typography/Text';
import Title from 'antd/lib/typography/Title';

import { getCore } from 'cvat-core-wrapper';
import GoBackButton from 'components/common/go-back-button';
import CVATLoadingSpinner from 'components/common/loading-spinner';

Chart.register(BarElement, CategoryScale, LinearScale, Tooltip);

const core = getCore();
const BAR_HEIGHT_PX = 22;

interface LabelCount {
    id: number;
    name: string;
    color: string;
    count: number;
}

type CountMode = 'shapes' | 'objects';

interface LabelCounts {
    task_id: number;
    count_mode: CountMode;
    total: number;
    labels: LabelCount[];
}

type PageState =
    { status: 'loading' } |
    { status: 'error', message: string } |
    { status: 'ready', counts: LabelCounts };

async function fetchLabelCounts(taskId: number, mode: CountMode): Promise<LabelCounts> {
    const response = await core.server.request(
        `${core.config.backendAPI}/test/tasks/${taskId}/label-counts`,
        { method: 'GET', params: { count: mode } },
    );
    return response.data;
}

function LabelCountsChart({ labels }: { labels: LabelCount[] }): JSX.Element {
    const shown = labels.filter((label) => label.count > 0).sort((a, b) => b.count - a.count);
    const unused = labels.length - shown.length;

    return (
        <>
            <div className='cvat-label-counts-chart' style={{ height: shown.length * BAR_HEIGHT_PX + 40 }}>
                <Bar
                    data={{
                        labels: shown.map((label) => label.name),
                        datasets: [{
                            label: 'Annotations',
                            data: shown.map((label) => label.count),
                            backgroundColor: shown.map((label) => label.color || '#1890ff'),
                        }],
                    }}
                    options={{
                        indexAxis: 'y',
                        maintainAspectRatio: false,
                        animation: false,
                        scales: { x: { beginAtZero: true } },
                    }}
                />
            </div>
            {unused > 0 && <Text type='secondary'>{`${unused} labels have no annotations and are not shown.`}</Text>}
        </>
    );
}

function LabelCountsPage(): JSX.Element {
    const taskId = +useParams<{ tid: string }>().tid;
    const [state, setState] = useState<PageState>({ status: 'loading' });
    const [mode, setMode] = useState<CountMode>('shapes');

    const load = useCallback(() => {
        setState({ status: 'loading' });
        fetchLabelCounts(taskId, mode)
            .then((counts) => setState({ status: 'ready', counts }))
            .catch((error: unknown) => setState({
                status: 'error',
                message: error instanceof Error ? error.message : String(error),
            }));
    }, [taskId, mode]);

    useEffect(load, [load]);

    let content: JSX.Element;
    if (state.status === 'loading') {
        content = <CVATLoadingSpinner />;
    } else if (state.status === 'error') {
        content = (
            <Result
                className='cvat-label-counts-error'
                status='error'
                title='Could not load the annotation counts'
                subTitle={state.message}
                extra={<Button type='primary' onClick={load}>Try again</Button>}
            />
        );
    } else if (state.counts.total === 0) {
        content = (
            <Empty
                className='cvat-label-counts-empty'
                description='This task has no annotations yet. Counts appear here once shapes, tracks or tags are saved.'
            />
        );
    } else {
        content = (
            <>
                <Text strong>{`${state.counts.total} ${mode === 'objects' ? 'objects' : 'annotations'}`}</Text>
                <LabelCountsChart labels={state.counts.labels} />
            </>
        );
    }

    return (
        <div className='cvat-label-counts-page'>
            <GoBackButton />
            <Title level={4}>{`Annotations per label, task #${taskId}`}</Title>
            <Radio.Group
                className='cvat-label-counts-mode'
                optionType='button'
                value={mode}
                onChange={(event) => setMode(event.target.value)}
                options={[
                    { value: 'shapes', label: 'Shapes', title: 'Every stored shape, track and tag counts once' },
                    {
                        value: 'objects',
                        label: 'Objects',
                        title: 'Shapes grouped together on one frame count as one object',
                    },
                ]}
            />
            {content}
        </div>
    );
}

export default React.memo(LabelCountsPage);
