// required to set height of pym iframes used in ONSEmbeddable block
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('div.pym-interactive').forEach(function (element) {
        return new pym.Parent(element.getAttribute('id'), element.dataset.url, {
            title: element.dataset.title
        });
    });
});
