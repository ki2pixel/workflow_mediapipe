// DOMDiff unit tests (Node/ESM)
// No external deps. We stub browser APIs required by DOMDiff.

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

// Minimal DOM mock
const Node = {
  ELEMENT_NODE: 1,
  TEXT_NODE: 3,
  COMMENT_NODE: 8
};
global.Node = Node;

class MockNode {
  constructor(nodeType, nodeName) {
    this.nodeType = nodeType;
    this.nodeName = nodeName;
    this.childNodes = [];
    this._parentNode = null;
  }

  get parentNode() { return this._parentNode; }
  
  appendChild(node) {
    if (node._parentNode) {
      node._parentNode.removeChild(node);
    }
    node._parentNode = this;
    this.childNodes.push(node);
    return node;
  }
  
  insertBefore(newNode, referenceNode) {
    if (newNode._parentNode) {
      newNode._parentNode.removeChild(newNode);
    }
    newNode._parentNode = this;
    if (!referenceNode) {
      this.childNodes.push(newNode);
    } else {
      const index = this.childNodes.indexOf(referenceNode);
      if (index === -1) throw new Error("referenceNode not found");
      this.childNodes.splice(index, 0, newNode);
    }
    return newNode;
  }
  
  removeChild(node) {
    const index = this.childNodes.indexOf(node);
    if (index !== -1) {
      this.childNodes.splice(index, 1);
      node._parentNode = null;
    }
    return node;
  }

  replaceWith(newNode) {
    if (this._parentNode) {
      this._parentNode.insertBefore(newNode, this);
      this._parentNode.removeChild(this);
    }
  }

  remove() {
    if (this._parentNode) {
      this._parentNode.removeChild(this);
    }
  }

  cloneNode(deep = false) {
    const clone = Object.assign(Object.create(Object.getPrototypeOf(this)), this);
    clone._parentNode = null;
    clone.childNodes = [];
    if (deep) {
      for (const child of this.childNodes) {
        clone.appendChild(child.cloneNode(true));
      }
    }
    return clone;
  }
}

class MockTextNode extends MockNode {
  constructor(text) {
    super(Node.TEXT_NODE, '#text');
    this.nodeValue = text;
  }
  cloneNode(deep = false) {
    return new MockTextNode(this.nodeValue);
  }
}

class MockElement extends MockNode {
  constructor(tagName) {
    super(Node.ELEMENT_NODE, tagName.toUpperCase());
    this.tagName = tagName.toUpperCase();
    this._attributes = new Map();
  }

  get attributes() {
    return Array.from(this._attributes.entries()).map(([name, value]) => ({ name, value }));
  }

  getAttribute(name) {
    return this._attributes.has(name) ? this._attributes.get(name) : null;
  }

  setAttribute(name, value) {
    this._attributes.set(name, String(value));
    if (name === 'id') this.id = value;
  }

  removeAttribute(name) {
    this._attributes.delete(name);
    if (name === 'id') this.id = undefined;
  }

  hasAttribute(name) {
    return this._attributes.has(name);
  }

  cloneNode(deep = false) {
    const clone = new MockElement(this.tagName);
    for (const [name, value] of this._attributes.entries()) {
      clone.setAttribute(name, value);
    }
    clone.id = this.id;
    clone.value = this.value;
    clone.checked = this.checked;
    clone.disabled = this.disabled;
    if (deep) {
      for (const child of this.childNodes) {
        clone.appendChild(child.cloneNode(true));
      }
    }
    return clone;
  }

  // Helper for test
  get innerHTML() {
    return this.childNodes.map(c => {
      if (c.nodeType === Node.TEXT_NODE) return c.nodeValue;
      let attrs = c.attributes.map(a => ` ${a.name}="${a.value}"`).join('');
      return `<${c.tagName.toLowerCase()}${attrs}>${c.innerHTML}</${c.tagName.toLowerCase()}>`;
    }).join('');
  }
}

global.document = {
  createElement: (tag) => {
    if (tag.toLowerCase() === 'template') {
      return {
        content: new MockElement('FRAGMENT'),
        set innerHTML(html) {
          // Extremely rudimentary HTML parser for tests
          this.content.childNodes = [];
          const div = new MockElement('DIV');
          // For test purposes, let's just create a child if there's html
          if (html.includes('<li')) {
             const li = new MockElement('LI');
             li.setAttribute('class', html.match(/class="([^"]+)"/)?.[1] || '');
             li.appendChild(new MockTextNode("Test"));
             this.content.appendChild(li);
          } else if (html.trim()) {
             this.content.appendChild(new MockTextNode(html));
          }
        }
      };
    }
    return new MockElement(tag);
  },
  createTextNode: (text) => new MockTextNode(text)
};

(async () => {
  try {
    const moduleUrl = new URL('../../static/utils/DOMDiff.js', import.meta.url);
    const mod = await import(moduleUrl);
    const { DOMDiff } = mod;

    // Test 1: Attribute morphing
    const realEl = new MockElement('div');
    realEl.setAttribute('class', 'old');
    realEl.setAttribute('data-remove', 'true');

    const virtualEl = new MockElement('div');
    virtualEl.setAttribute('class', 'new');
    virtualEl.setAttribute('data-add', 'true');

    DOMDiff._morphNode(realEl, virtualEl);
    
    assert(realEl.getAttribute('class') === 'new', 'Class should be updated');
    assert(!realEl.hasAttribute('data-remove'), 'Old attribute should be removed');
    assert(realEl.getAttribute('data-add') === 'true', 'New attribute should be added');

    // Test 2: Text node morphing
    const realText = new MockTextNode('Hello');
    const virtualText = new MockTextNode('World');
    DOMDiff._morphNode(realText, virtualText);
    assert(realText.nodeValue === 'World', 'Text value should be morphed');

    // Test 3: Children morphing (addition and removal)
    const realList = new MockElement('ul');
    realList.appendChild(new MockElement('li'));
    realList.appendChild(new MockElement('li'));

    const virtualList = new MockElement('ul');
    virtualList.appendChild(new MockElement('li')); // 1 remaining
    virtualList.appendChild(new MockElement('li')); // 2 remaining
    virtualList.appendChild(new MockElement('li')); // 1 added

    DOMDiff._morphNode(realList, virtualList);
    assert(realList.childNodes.length === 3, `Expected 3 children, got ${realList.childNodes.length}`);

    // Test 4: Keyed elements reordering
    const rKeyed = new MockElement('div');
    const r1 = new MockElement('span'); r1.setAttribute('data-key', '1'); r1.appendChild(new MockTextNode('one'));
    const r2 = new MockElement('span'); r2.setAttribute('data-key', '2'); r2.appendChild(new MockTextNode('two'));
    rKeyed.appendChild(r1);
    rKeyed.appendChild(r2);

    const vKeyed = new MockElement('div');
    const v2 = new MockElement('span'); v2.setAttribute('data-key', '2'); v2.appendChild(new MockTextNode('two-updated'));
    const v1 = new MockElement('span'); v1.setAttribute('data-key', '1'); v1.appendChild(new MockTextNode('one-updated'));
    vKeyed.appendChild(v2);
    vKeyed.appendChild(v1);

    DOMDiff._morphNode(rKeyed, vKeyed);
    assert(rKeyed.childNodes[0] === r2, 'Node 2 should have moved to first position');
    assert(rKeyed.childNodes[1] === r1, 'Node 1 should have moved to second position');
    assert(r2.childNodes[0].nodeValue === 'two-updated', 'Node 2 text should be updated');

    console.log('DOMDiff performance/robustness test: OK');
    process.exit(0);
  } catch (err) {
    console.error('DOMDiff performance/robustness test failed:', err);
    process.exit(1);
  }
})();
