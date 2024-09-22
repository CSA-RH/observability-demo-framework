import React, { useEffect, useState, useRef } from 'react';
import cytoscape from 'cytoscape';

const AgentCanvas = ({ onAgentSelect, locked, simulation, onSimulationUpdated }) => {
    const cyRef = useRef(null);
    const [cytoscapeInstance, setCytoscapeInstance] = useState(null);
    // Create a ref to track the latest value of locked
    const lockedRef = useRef(locked);

    useEffect(() => {
        // Initialize Cytoscape instance when the component mounts
        const cy = cytoscape({
            container: cyRef.current, // Reference to the DOM element
            style: [
                {
                    selector: 'node',
                    style: {
                        //shape: 'hexagon',
                        'background-color': 'red',
                        label: 'data(id)'
                    }
                },
                {
                    selector: 'node:selected',
                    style: {
                        'background-color': '#FF5733', // Color when the node is selected
                        'border-color': '#000',
                        'border-width': 3
                    }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#ccc',
                        'target-arrow-color': '#ccc',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier'
                    }
                }
            ],
            layout: {
                name: 'grid',
                rows: 1
            },
            // Disable zoom
            zoomingEnabled: false,
            userZoomingEnabled: false,

            // Optionally set min and max zoom
            minZoom: 1,  // Minimum zoom level
            maxZoom: 1,  // Maximum zoom level

            // Initial zoom
            zoom: 1,

            // Disable user panning
            userPanningEnabled: false,

            // Disable box selection
            boxSelectionEnabled: false,
        });

        let selectedNodes = [];

        function updateStructure(evt) {
            console.log("updateStructure. Canvas Locked: ", locked);
            if (lockedRef.current) {
                return;
            }

            const allElements = cy.elements();  // Get all nodes and edges            
            const structure = allElements.map((element) => {
                if (element.isNode()) {
                    return {
                        group: 'nodes',
                        data: element.data(),
                        position: element.position(),
                    };
                } else if (element.isEdge()) {
                    return {
                        group: 'edges',
                        data: element.data(),
                    };
                }
            });

            // Notify parent of the updated structure
            onSimulationUpdated(structure);
        }

        // List of names
        const malagaPlayers = [
            "duda",
            "sandro-ramirez",
            "isco",
            "roque-santa-cruz",
            "salva-ballesta",
            "roteta",
            "koke",
            "weligton",
            "santi-cazorla",            
            "nacho",
            "pablo-fornals",
            "van-nistelrooy",
            "kiki-musampa",
            "fernando-hierro",
            "rufete",
            "apono",
            "roberto-rosales",
            "vicente-valcarce",
            "jesus-gamez",
            "enzo-maresca",
            "julio-baptista",
            "amrabat",
            "charles-dias",
            "joaquin-sanchez",
            "samuel-garcia",
            "eliseu",
            "victor-sanchez-del-amo",
            "carlos-kameni",
            "ignacio-camacho",
            "javi-gracia",
            "ibon-bieir",
            "willy-caballero",
            "migueli",
            "antonio-hidalgo",
            "pepillo",
            "basti",
            "manuel-sanchez-delgado-manolo",
            "dani-bautista",
            "josemi",
            "sandro",
            "monreal",
            "quino",
            "juanmi",
            "nacho-perez",
            "adolfo-aldana",
            "ivo-vukcevic",
            "manuel-fernandez",
            "martin-aguilar",
            "manolo-reina",
            "emerson",
            "adrian-gonzalez",
            "victor-vincent",
            "albert-luque",
            "panadero-diaz",
            "ricardinho",
            "gerardo-torres",
            "ivan-cordoba",
            "rafa-zaragoza",
            "youssef-en-nesyri",
            "eliseo-salazar",
            "marcelo-romero",
            "antonio-gayoso",
            "marcos-angeleri",
            "juan-calatayud",
            "roberto-santamaria",
            "diego-rolan",
            "borja-baston",
            "nordin-amrabat",
            "sergio-pellicer",
            "francis",
            "manu",
            "munir-mohand",
            "mehdi-lacen",
            "jose-anselmo",
            "pedro",
            "alvaro-sanz",
            "fabrice-olinga",
            "charles",
            "sandro-bergara",
            "jeremy-toulalan",
            "pedro-c-camara",
            "ismael-gutierrez",
            "antonio-benitez",
            "ivan-lucas",
            "jose-paz",
            "diego-benitez",
            "adrian",
            "dani-carrera",
            "esteban-suarez",
            "samuel-munoz",
            "diego-gonzalez",
            "junior-sarmiento",
            "alfredo-mejias",
            "dario-silva",
            "movilla",
            "antonito"
        ];

        // Function to randomly select a name without repeating
        function getRandomName() {
            if (malagaPlayers.length === 0) {
                console.log("All names have been used.");
                return null; // or reset the array if needed
            }

            // Get a random index
            const randomIndex = Math.floor(Math.random() * malagaPlayers.length);

            // Extract the name
            const selectedName = malagaPlayers.splice(randomIndex, 1)[0];

            // Return the selected name
            return selectedName;
        }

        function addNode(position) {
            cy.add({
                group: 'nodes',
                data: { id: getRandomName() },
                position: { x: position.x, y: position.y }
            });
        }

        cy.on('add remove', updateStructure);

        cy.on('add', 'node', function (event) {
            if (lockedRef.current) {
                return;
            }
            const addedNode = event.target; // The newly added node

            onAgentSelect(addedNode.data());
        });

        // Right-click (context tap) event listener for nodes
        cy.on('cxttap', 'node', function (event) {
            if (lockedRef.current) {
                return;
            }
            var node = event.target;
            node.remove();  // Removes the clicked node
        });

        // Right-click (context tap) event listener for edges
        cy.on('cxttap', 'edge', function (event) {
            if (lockedRef.current) {
                return;
            }
            var edge = event.target;
            edge.remove();  // Removes the clicked edge
        });

        // Right-click (context tap) event listener for edges
        cy.on('cxttap', function (event) {
            cy.elements().unselect();
            selectedNodes = [];
            onAgentSelect(null);
        });

        // Function to check if an edge with a specific name exists
        function edgeExists(name) {
            return cy.edges(`[id = "${name}"]`).length > 0;
        }

        cy.on('tap', function (evt) {
            if (lockedRef.current) {
                return;
            }
            const position = evt.position;
            if (evt.target === cy) {
                addNode(position);
            }
        })

        cy.on('tap', 'node', function (evt) {
            const clickedNode = evt.target;
            // Update the selected agent
            onAgentSelect(clickedNode.data());            

            if (lockedRef.current) {
                return;
            }

            selectedNodes.push(clickedNode);

            if (selectedNodes.length === 2) {
                const sourceNode = selectedNodes[0];
                const targetNode = selectedNodes[1];

                const edgeId = 'edge_' + sourceNode.id() + '_' + targetNode.id();
                if (!edgeExists(edgeId)) {
                    cy.add({
                        group: 'edges',
                        data: {
                            id: edgeId,
                            source: sourceNode.id(),
                            target: targetNode.id()
                        }
                    });
                    targetNode.unselect();
                }

                selectedNodes = [];
            }
        });

        setCytoscapeInstance(cy);

        // Cleanup the instance when the component is unmounted
        return () => cy.destroy();
    }, []);

    // This effect runs whenever the `simulation` changes
    useEffect(() => {
        // reset the graphic.
        if (cytoscapeInstance && simulation?.length === 0) {
            console.log("Cleaning the elements....")
            cytoscapeInstance.elements().remove();  // Clear the old elements                        
        }
        // load the graphic if simulation is fetched. 
        if (cytoscapeInstance?.elements().length === 0 && simulation?.length > 0) {
            // Create all nodes. 
            console.log("Update the visualization")
            simulation.forEach(element => {
                if (element.group === 'nodes') {
                    cytoscapeInstance.add({
                        group: 'nodes',
                        data: element.data,
                        position: element.position
                    });
                } else if (element.group === 'edges') {
                    cytoscapeInstance.add({
                        group: 'edges',
                        data: element.data
                    });
                }
            });
        }
    }, [simulation, cytoscapeInstance]);  // Run whenever `simulation` or `cytoscapeInstance` changes

    useEffect(() => {
        lockedRef.current = locked;

        if (!cytoscapeInstance) return;
        if (locked) {
            cytoscapeInstance.nodes().ungrabify(); // Prevent nodes from being moved
        }
        else {
            cytoscapeInstance.nodes().grabify(); // Allow nodes to be moved
        }

    }, [locked, cytoscapeInstance])


    return <div ref={cyRef} style={{ width: '590px', height: '400px', border: '1px solid black', margin: '5px' }} />;
};

export default AgentCanvas;
