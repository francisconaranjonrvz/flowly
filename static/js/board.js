// Drag & drop de tarjetas y columnas + cierre de menus
// Es el único JS del proyecto (aparte de toggles inline en los templates)

(function () {
  'use strict';

  var boardEl = document.getElementById('board');
  if (!boardEl) return;

  var boardId = boardEl.dataset.boardId;
  var csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  var draggedEl = null;
  var dragKind = null; // 'card' o 'column'
  var dragGhost = null; // clon que se ve "en la mano" al arrastrar

  // Crea una imagen de arrastre propia (la tarjeta inclinada con sombra) para
  // que se vea claramente qué se está moviendo.
  function setCardDragImage(e, card) {
    var rect = card.getBoundingClientRect();
    var ghost = card.cloneNode(true);
    ghost.classList.remove('is-dragging');
    ghost.style.position = 'fixed';
    ghost.style.top = '-9999px';
    ghost.style.left = '0';
    ghost.style.width = rect.width + 'px';
    ghost.style.margin = '0';
    ghost.style.opacity = '1';
    ghost.style.transform = 'rotate(3deg)';
    ghost.style.boxShadow = '0 14px 28px rgba(0,0,0,0.35)';
    ghost.style.pointerEvents = 'none';
    document.body.appendChild(ghost);
    dragGhost = ghost;
    try {
      e.dataTransfer.setDragImage(ghost, e.clientX - rect.left, e.clientY - rect.top);
    } catch (err) { /* navegadores sin setDragImage: usan el por defecto */ }
  }

  // --- Drag start ---
  boardEl.addEventListener('dragstart', function (e) {
    var card = e.target.closest('.card');
    if (card) {
      dragKind = 'card';
      draggedEl = card;
      card.classList.add('is-dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', card.dataset.cardId);
      setCardDragImage(e, card);
      requestAnimationFrame(function () { card.style.opacity = '0.4'; });
      return;
    }

    var col = e.target.closest('.column');
    if (col) {
      dragKind = 'column';
      draggedEl = col;
      col.classList.add('is-dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', 'col:' + col.dataset.columnId);
    }
  });

  // --- Drag over ---
  boardEl.addEventListener('dragover', function (e) {
    if (dragKind === 'column') {
      var overCol = e.target.closest('.column');
      if (!overCol || overCol === draggedEl) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      return;
    }

    var zone = e.target.closest('.column__cards');
    if (!zone || !draggedEl) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    zone.classList.add('is-drop-target');
    positionIndicator(zone, e.clientY);
  });

  // --- Drag leave ---
  boardEl.addEventListener('dragleave', function (e) {
    var zone = e.target.closest('.column__cards');
    if (!zone) return;
    if (!zone.contains(e.relatedTarget)) {
      zone.classList.remove('is-drop-target');
      removeIndicator(zone);
    }
  });

  // --- Drop ---
  boardEl.addEventListener('drop', function (e) {
    e.preventDefault();

    if (dragKind === 'column' && draggedEl) {
      var overCol = e.target.closest('.column');
      if (overCol && overCol !== draggedEl) {
        var cols = Array.from(boardEl.querySelectorAll('.column'));
        var ids = cols.map(function (c) { return c.dataset.columnId; })
                      .filter(function (id) { return id !== draggedEl.dataset.columnId; });
        var idx = ids.indexOf(overCol.dataset.columnId);
        var rect = overCol.getBoundingClientRect();
        if (e.clientX > rect.left + rect.width / 2) idx += 1;

        postJSON('/board/' + boardId + '/column/move/', {
          column_id: parseInt(draggedEl.dataset.columnId),
          order: idx,
        }).then(function () { location.reload(); });
      }
      cleanup();
      return;
    }

    var zone = e.target.closest('.column__cards');
    if (!zone || !draggedEl) { cleanup(); return; }

    var toColumnId = zone.dataset.columnId;
    var cardId = draggedEl.dataset.cardId;
    var order = getDropIndex(zone, e.clientY);

    // Mover visualmente al instante
    removeIndicator(zone);
    var ref = zone.querySelectorAll('.card')[order];
    if (ref) zone.insertBefore(draggedEl, ref);
    else zone.appendChild(draggedEl);

    cleanup();

    postJSON('/board/' + boardId + '/card/move/', {
      card_id: parseInt(cardId),
      column_id: parseInt(toColumnId),
      order: order,
    }).then(function () { location.reload(); });
  });

  // --- Drag end ---
  boardEl.addEventListener('dragend', function () {
    cleanup();
  });

  // --- Helpers ---

  function getDropIndex(zone, mouseY) {
    var cards = Array.from(zone.querySelectorAll('.card'))
      .filter(function (c) { return c !== draggedEl; });
    for (var i = 0; i < cards.length; i++) {
      var rect = cards[i].getBoundingClientRect();
      if (mouseY < rect.top + rect.height / 2) return i;
    }
    return cards.length;
  }

  function positionIndicator(zone, mouseY) {
    var ind = zone.querySelector('.drop-indicator');
    if (!ind) {
      ind = document.createElement('div');
      ind.className = 'drop-indicator';
      zone.appendChild(ind);
    }
    var cards = Array.from(zone.querySelectorAll('.card'))
      .filter(function (c) { return c !== draggedEl; });
    var idx = getDropIndex(zone, mouseY);
    if (idx >= cards.length) zone.appendChild(ind);
    else cards[idx].insertAdjacentElement('beforebegin', ind);
  }

  function removeIndicator(zone) {
    var ind = zone.querySelector('.drop-indicator');
    if (ind) ind.remove();
  }

  function cleanup() {
    if (dragGhost) {
      dragGhost.remove();
      dragGhost = null;
    }
    if (draggedEl) {
      draggedEl.classList.remove('is-dragging');
      draggedEl.style.opacity = '';
    }
    boardEl.querySelectorAll('.is-drop-target').forEach(function (el) {
      el.classList.remove('is-drop-target');
    });
    boardEl.querySelectorAll('.drop-indicator').forEach(function (el) {
      el.remove();
    });
    draggedEl = null;
    dragKind = null;
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify(body),
    });
  }

  // Los menús de columna y los formularios inline (abrir/cerrar, Escape,
  // clic-fuera) los gestiona Alpine en board.html.
})();
