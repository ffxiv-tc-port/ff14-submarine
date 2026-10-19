export function getRouteTimeCostText(time: number, speed: number) {
    let min = time / speed + 12 * 60; // 航行基礎時間 12 小時
    const day = min >= 24 * 60 ? Math.floor(min / (24 * 60)) : 0;
    const hour = Math.floor((min % (24 * 60)) / 60);
    min = Math.floor(min % 60);
    return (day > 0 ? day + '日' : '') + hour + '小時' + min + '分';
}

export function getRouteRealTimeText(time_base: number, time: number, speed: number) {
    const t = new Date(time_base + (12 * 60 + time / speed) * 60 * 1000);
    const fixTimeLength = (num: number) => {
        return num < 10 ? '0' + num : num;
    };
    return (
        t.getFullYear() +
        '/' +
        (t.getMonth() + 1) +
        '/' +
        t.getDate() +
        ' ' +
        fixTimeLength(t.getHours()) +
        ':' +
        fixTimeLength(t.getMinutes())
    );
}
